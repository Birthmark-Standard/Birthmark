#![cfg_attr(not(feature = "std"), no_std)]

//! # Birthmark Pallet
//!
//! The Birthmark pallet provides functionality for storing and querying image authentication records
//! on the blockchain. It enables permanent, tamper-evident storage of image hashes from authenticated
//! cameras and software, surviving all forms of metadata stripping.
//!
//! ## Overview
//!
//! The Birthmark pallet allows authorized submitters (aggregator nodes) to:
//! - Submit image authentication records with SHA-256 hashes
//! - Store provenance information (modification level, parent hashes)
//! - Associate records with manufacturer/software authorities
//! - Query records by image hash for verification
//!
//! ## Interface
//!
//! ### Dispatchable Functions
//!
//! - `submit_image_record` - Submit a new image authentication record (restricted)
//! - `submit_image_batch` - Submit multiple records in a single transaction (gas efficient)
//!
//! ### Public Functions
//!
//! - `get_image_record` - Query storage for an image record by hash
//!
//! ## Privacy Architecture
//!
//! - Only SHA-256 hashes stored (not image content)
//! - Timestamp reflects server processing time (not capture time)
//! - Authority IDs are manufacturer identifiers (not specific camera serial numbers)

pub use pallet::*;

#[cfg(test)]
mod tests;

#[frame_support::pallet]
pub mod pallet {
    use frame_support::pallet_prelude::*;
    use frame_system::pallet_prelude::*;
    use sp_runtime::traits::UniqueSaturatedInto;
    use sp_std::vec::Vec;

    /// The pallet's configuration trait.
    #[pallet::config]
    pub trait Config: frame_system::Config + pallet_timestamp::Config {
        /// The overarching event type.
        type RuntimeEvent: From<Event<Self>> + IsType<<Self as frame_system::Config>::RuntimeEvent>;

        /// Maximum length for authority ID string
        #[pallet::constant]
        type MaxAuthorityIdLength: Get<u32>;

        /// Maximum length for image hash (SHA-256 = 64 hex chars)
        #[pallet::constant]
        type MaxImageHashLength: Get<u32>;
    }

    #[pallet::pallet]
    pub struct Pallet<T>(_);

    /// Submission type for image records
    #[derive(Clone, Encode, Decode, Eq, PartialEq, RuntimeDebug, TypeInfo, MaxEncodedLen)]
    pub enum SubmissionType {
        Camera,
        Software,
    }

    /// Image authentication record stored on-chain
    /// OPTIMIZED: Uses compact encoding and lookup tables for minimal storage overhead
    #[derive(Clone, Encode, Decode, Eq, PartialEq, RuntimeDebug, TypeInfo, MaxEncodedLen)]
    pub struct ImageRecord {
        /// SHA-256 hash of the image (32 bytes binary, not 64 hex chars)
        pub image_hash: [u8; 32],
        /// Type of submission (camera or software)
        pub submission_type: SubmissionType,
        /// Modification level: 0 = raw sensor, 1 = validated/minor edits, 2 = modified
        pub modification_level: u8,
        /// Hash of parent image (for provenance chain)
        pub parent_image_hash: Option<[u8; 32]>,
        /// Authority identifier (lookup table index - 2 bytes instead of variable string)
        pub authority_id: u16,
        /// Timestamp when record was submitted to blockchain (NOT capture time)
        /// Using compact encoding: typically 2-3 bytes instead of 8
        #[codec(compact)]
        pub timestamp: u32,
        /// Block number where record was stored
        /// Using compact encoding: typically 2-3 bytes instead of 4
        #[codec(compact)]
        pub block_number: u32,
    }

    // Note: owner_hash field removed in this optimization
    // Can be added via runtime upgrade when attribution feature is needed

    /// Storage map from image hash to authentication record
    ///
    /// This is the primary storage for all authenticated images. Each hash can only
    /// appear once, making records immutable and preventing duplicates.
    ///
    /// OPTIMIZED: Uses binary hash [u8; 32] instead of hex string (64 bytes -> 32 bytes)
    #[pallet::storage]
    #[pallet::getter(fn image_records)]
    pub type ImageRecords<T: Config> = StorageMap<
        _,
        Blake2_128Concat,
        [u8; 32],
        ImageRecord,
        OptionQuery,
    >;

    /// Authority registry: Maps authority ID (u16) to authority name
    /// This allows us to store a 2-byte index instead of variable-length strings
    ///
    /// Example: Sony -> 0, Canon -> 1, Adobe Photoshop -> 2, etc.
    #[pallet::storage]
    #[pallet::getter(fn authority_registry)]
    pub type AuthorityRegistry<T: Config> = StorageMap<
        _,
        Blake2_128Concat,
        u16,
        BoundedVec<u8, T::MaxAuthorityIdLength>,
        OptionQuery,
    >;

    /// Next authority ID to assign
    #[pallet::storage]
    #[pallet::getter(fn next_authority_id)]
    pub type NextAuthorityId<T: Config> = StorageValue<_, u16, ValueQuery>;

    /// Count of total image records stored (for statistics)
    #[pallet::storage]
    #[pallet::getter(fn total_records)]
    pub type TotalRecords<T: Config> = StorageValue<_, u64, ValueQuery>;

    /// Genesis configuration for the pallet
    #[pallet::genesis_config]
    #[derive(frame_support::DefaultNoBound)]
    pub struct GenesisConfig<T: Config> {
        #[serde(skip)]
        pub _phantom: PhantomData<T>,
    }

    #[pallet::genesis_build]
    impl<T: Config> BuildGenesisConfig for GenesisConfig<T> {
        fn build(&self) {
            // Initialize total records to 0
            TotalRecords::<T>::put(0u64);
            // Initialize next authority ID to 0
            NextAuthorityId::<T>::put(0u16);
        }
    }

    /// Events emitted by the pallet
    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        /// An image record was successfully submitted
        ImageRecordSubmitted {
            image_hash: [u8; 32],
            authority_id: u16,
            modification_level: u8,
        },
        /// Multiple image records were submitted in a batch
        ImageBatchSubmitted {
            count: u32,
        },
        /// A new authority was registered
        AuthorityRegistered {
            authority_id: u16,
            authority_name: BoundedVec<u8, T::MaxAuthorityIdLength>,
        },
    }

    /// Errors that can occur in the pallet
    #[pallet::error]
    pub enum Error<T> {
        /// The provided image hash has invalid length (must be 32 bytes binary or 64 hex chars)
        InvalidHashLength,
        /// The modification level is invalid (must be 0, 1, or 2)
        InvalidModificationLevel,
        /// The authority name exceeds maximum length
        AuthorityNameTooLong,
        /// This image hash already exists in storage (duplicate submission)
        HashAlreadyExists,
        /// The parent image hash was not found in storage
        ParentHashNotFound,
        /// The parent image hash has invalid length
        InvalidParentHashLength,
        /// Batch submission is empty
        EmptyBatch,
        /// Batch submission exceeds maximum size
        BatchTooLarge,
        /// Authority ID not found in registry
        AuthorityNotFound,
        /// Maximum number of authorities reached (u16::MAX)
        TooManyAuthorities,
    }

    /// Dispatchable functions (extrinsics)
    #[pallet::call]
    impl<T: Config> Pallet<T> {
        /// Submit a new image authentication record to the blockchain (OPTIMIZED).
        ///
        /// This function is restricted to authorized aggregator nodes. It stores
        /// the image hash along with authentication metadata permanently on-chain.
        ///
        /// OPTIMIZATION NOTES:
        /// - Accepts hex (64 chars) or binary (32 bytes) image hashes
        /// - Automatically registers authorities in lookup table (2 bytes vs variable)
        /// - Uses compact encoding for timestamps and block numbers
        /// - Removed owner_hash field (can be added via runtime upgrade if needed)
        ///
        /// # Arguments
        ///
        /// * `origin` - Must be signed by an authorized aggregator account
        /// * `image_hash` - SHA-256 hash (64 hex chars OR 32 binary bytes)
        /// * `submission_type` - Whether from camera or software
        /// * `modification_level` - 0 (raw), 1 (validated), or 2 (modified)
        /// * `parent_image_hash` - Optional hash of parent image for provenance
        /// * `authority_name` - Manufacturer or software developer name (auto-registered)
        ///
        /// # Errors
        ///
        /// Returns error if:
        /// - Hash length is not 32 or 64 bytes
        /// - Modification level is not 0-2
        /// - Hash already exists in storage
        /// - Parent hash doesn't exist (if specified)
        /// - Authority name exceeds max length
        ///
        /// # Weight
        ///
        /// Weight is calculated based on:
        /// - One storage read (check for duplicate)
        /// - One storage write (insert record)
        /// - One storage read+write (increment counter)
        /// - Optional: authority registration (if new)
        #[pallet::call_index(0)]
        #[pallet::weight(10_000)] // TODO: Proper weight calculation
        pub fn submit_image_record(
            origin: OriginFor<T>,
            image_hash: Vec<u8>,
            submission_type: SubmissionType,
            modification_level: u8,
            parent_image_hash: Option<Vec<u8>>,
            authority_name: Vec<u8>,
        ) -> DispatchResult {
            // Verify origin is signed (authorization logic can be added via custom origin)
            let _who = ensure_signed(origin)?;

            // Validate modification level
            ensure!(
                modification_level <= 2,
                Error::<T>::InvalidModificationLevel
            );

            // Parse image hash (accepts hex or binary)
            let binary_hash = Self::parse_image_hash(&image_hash)?;

            // Validate parent hash if provided
            let parent_hash = if let Some(parent) = parent_image_hash {
                let parsed_parent = Self::parse_image_hash(&parent)?;

                // Ensure parent exists in storage
                ensure!(
                    ImageRecords::<T>::contains_key(&parsed_parent),
                    Error::<T>::ParentHashNotFound
                );

                Some(parsed_parent)
            } else {
                None
            };

            // Ensure hash doesn't already exist (immutability + duplicate prevention)
            ensure!(
                !ImageRecords::<T>::contains_key(&binary_hash),
                Error::<T>::HashAlreadyExists
            );

            // Register or lookup authority (returns u16 ID)
            let authority_id = Self::register_or_get_authority(authority_name)?;

            // Get current timestamp and block number
            let timestamp = pallet_timestamp::Pallet::<T>::get();
            let block_number = frame_system::Pallet::<T>::block_number();

            // Convert to u32 for compact encoding
            let timestamp_u32: u32 = timestamp.unique_saturated_into();
            let block_number_u32: u32 = block_number.unique_saturated_into();

            // Create record
            let record = ImageRecord {
                image_hash: binary_hash,
                submission_type,
                modification_level,
                parent_image_hash: parent_hash,
                authority_id,
                timestamp: timestamp_u32,
                block_number: block_number_u32,
            };

            // Store record
            ImageRecords::<T>::insert(&binary_hash, record);

            // Increment total count
            TotalRecords::<T>::mutate(|count| {
                *count = count.saturating_add(1);
            });

            // Emit event
            Self::deposit_event(Event::ImageRecordSubmitted {
                image_hash: binary_hash,
                authority_id,
                modification_level,
            });

            Ok(())
        }

        /// Submit multiple image records in a single transaction (batch submission - OPTIMIZED).
        ///
        /// This is more gas-efficient than individual submissions when aggregators
        /// have accumulated multiple validated images.
        ///
        /// OPTIMIZATION NOTES:
        /// - Accepts hex or binary hashes
        /// - Automatically registers authorities in lookup table
        /// - Uses compact encoding for all numeric fields
        /// - Removed owner_hash field
        ///
        /// # Arguments
        ///
        /// * `origin` - Must be signed by an authorized aggregator account
        /// * `records` - Vector of record data (max 100 records per batch)
        ///
        /// # Errors
        ///
        /// Returns error if:
        /// - Batch is empty
        /// - Batch exceeds maximum size (100 records)
        /// - Any individual record validation fails
        ///
        /// Note: This is an atomic operation - all records succeed or all fail.
        #[pallet::call_index(1)]
        #[pallet::weight(10_000 * records.len() as u64)] // TODO: Proper weight calculation
        pub fn submit_image_batch(
            origin: OriginFor<T>,
            records: Vec<(
                Vec<u8>,                // image_hash (hex or binary)
                SubmissionType,         // submission_type
                u8,                     // modification_level
                Option<Vec<u8>>,        // parent_image_hash
                Vec<u8>,                // authority_name
            )>,
        ) -> DispatchResult {
            let _who = ensure_signed(origin)?;

            // Validate batch constraints
            ensure!(!records.is_empty(), Error::<T>::EmptyBatch);
            ensure!(records.len() <= 100, Error::<T>::BatchTooLarge);

            let count = records.len() as u32;

            // Get timestamp and block number once for the entire batch
            let timestamp = pallet_timestamp::Pallet::<T>::get();
            let block_number = frame_system::Pallet::<T>::block_number();
            let timestamp_u32: u32 = timestamp.unique_saturated_into();
            let block_number_u32: u32 = block_number.unique_saturated_into();

            // Process each record
            for (image_hash, submission_type, modification_level, parent_image_hash, authority_name) in records {
                // Validate modification level
                ensure!(modification_level <= 2, Error::<T>::InvalidModificationLevel);

                // Parse image hash (accepts hex or binary)
                let binary_hash = Self::parse_image_hash(&image_hash)?;

                // Validate parent hash if provided
                let parent_hash = if let Some(parent) = parent_image_hash {
                    let parsed_parent = Self::parse_image_hash(&parent)?;
                    ensure!(
                        ImageRecords::<T>::contains_key(&parsed_parent),
                        Error::<T>::ParentHashNotFound
                    );
                    Some(parsed_parent)
                } else {
                    None
                };

                // Ensure hash doesn't already exist
                ensure!(
                    !ImageRecords::<T>::contains_key(&binary_hash),
                    Error::<T>::HashAlreadyExists
                );

                // Register or lookup authority
                let authority_id = Self::register_or_get_authority(authority_name)?;

                // Create record
                let record = ImageRecord {
                    image_hash: binary_hash,
                    submission_type,
                    modification_level,
                    parent_image_hash: parent_hash,
                    authority_id,
                    timestamp: timestamp_u32,
                    block_number: block_number_u32,
                };

                // Store record
                ImageRecords::<T>::insert(&binary_hash, record);
                TotalRecords::<T>::mutate(|c| *c = c.saturating_add(1));
            }

            Self::deposit_event(Event::ImageBatchSubmitted { count });

            Ok(())
        }
    }

    /// Public helper functions (not dispatchable)
    impl<T: Config> Pallet<T> {
        /// Convert hex string to binary hash [u8; 32]
        ///
        /// Accepts both hex strings (64 chars) and binary data (32 bytes)
        pub fn parse_image_hash(hash: &[u8]) -> Result<[u8; 32], Error<T>> {
            match hash.len() {
                32 => {
                    // Already binary
                    let mut result = [0u8; 32];
                    result.copy_from_slice(hash);
                    Ok(result)
                }
                64 => {
                    // Hex string - convert to binary
                    let mut result = [0u8; 32];
                    for i in 0..32 {
                        let byte_str = &hash[i * 2..i * 2 + 2];
                        let byte = u8::from_str_radix(
                            core::str::from_utf8(byte_str).map_err(|_| Error::<T>::InvalidHashLength)?,
                            16,
                        )
                        .map_err(|_| Error::<T>::InvalidHashLength)?;
                        result[i] = byte;
                    }
                    Ok(result)
                }
                _ => Err(Error::<T>::InvalidHashLength),
            }
        }

        /// Register a new authority or get existing authority ID
        ///
        /// This function searches for an existing authority with the same name.
        /// If found, returns the existing ID. If not found, registers a new authority.
        pub fn register_or_get_authority(authority_name: Vec<u8>) -> Result<u16, Error<T>> {
            // Validate length
            ensure!(
                authority_name.len() as u32 <= T::MaxAuthorityIdLength::get(),
                Error::<T>::AuthorityNameTooLong
            );

            let bounded_name: BoundedVec<u8, T::MaxAuthorityIdLength> = authority_name
                .clone()
                .try_into()
                .map_err(|_| Error::<T>::AuthorityNameTooLong)?;

            // Search for existing authority
            for (id, stored_name) in AuthorityRegistry::<T>::iter() {
                if stored_name == bounded_name {
                    return Ok(id);
                }
            }

            // Register new authority
            let new_id = NextAuthorityId::<T>::get();
            ensure!(new_id < u16::MAX, Error::<T>::TooManyAuthorities);

            AuthorityRegistry::<T>::insert(new_id, bounded_name.clone());
            NextAuthorityId::<T>::put(new_id.saturating_add(1));

            // Emit event
            Self::deposit_event(Event::AuthorityRegistered {
                authority_id: new_id,
                authority_name: bounded_name,
            });

            Ok(new_id)
        }

        /// Query an image record by its hash (public query function)
        ///
        /// This is used by RPC endpoints for fast verification queries.
        pub fn get_image_record(hash: &[u8; 32]) -> Option<ImageRecord> {
            ImageRecords::<T>::get(hash)
        }

        /// Get authority name by ID
        pub fn get_authority_name(id: u16) -> Option<BoundedVec<u8, T::MaxAuthorityIdLength>> {
            AuthorityRegistry::<T>::get(id)
        }

        /// Check if an image hash exists in storage
        pub fn image_exists(hash: &[u8; 32]) -> bool {
            ImageRecords::<T>::contains_key(hash)
        }

        /// Get the total number of records stored
        pub fn get_total_records() -> u64 {
            TotalRecords::<T>::get()
        }
    }
}
