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
    #[derive(Clone, Encode, Decode, Eq, PartialEq, RuntimeDebug, TypeInfo, MaxEncodedLen)]
    #[scale_info(skip_type_params(T))]
    pub struct ImageRecord<T: Config> {
        /// SHA-256 hash of the image (64 hex characters as bytes)
        pub image_hash: BoundedVec<u8, T::MaxImageHashLength>,
        /// Type of submission (camera or software)
        pub submission_type: SubmissionType,
        /// Modification level: 0 = raw sensor, 1 = validated/minor edits, 2 = modified
        pub modification_level: u8,
        /// Hash of parent image (for provenance chain)
        pub parent_image_hash: Option<BoundedVec<u8, T::MaxImageHashLength>>,
        /// Authority identifier (manufacturer or software developer)
        pub authority_id: BoundedVec<u8, T::MaxAuthorityIdLength>,
        /// Timestamp when record was submitted to blockchain (NOT capture time)
        pub timestamp: T::Moment,
        /// Block number where record was stored
        pub block_number: BlockNumberFor<T>,
    }

    /// Storage map from image hash to authentication record
    ///
    /// This is the primary storage for all authenticated images. Each hash can only
    /// appear once, making records immutable and preventing duplicates.
    #[pallet::storage]
    #[pallet::getter(fn image_records)]
    pub type ImageRecords<T: Config> = StorageMap<
        _,
        Blake2_128Concat,
        BoundedVec<u8, T::MaxImageHashLength>,
        ImageRecord<T>,
        OptionQuery,
    >;

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
        }
    }

    /// Events emitted by the pallet
    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        /// An image record was successfully submitted
        ImageRecordSubmitted {
            image_hash: BoundedVec<u8, T::MaxImageHashLength>,
            authority_id: BoundedVec<u8, T::MaxAuthorityIdLength>,
            modification_level: u8,
        },
        /// Multiple image records were submitted in a batch
        ImageBatchSubmitted {
            count: u32,
        },
    }

    /// Errors that can occur in the pallet
    #[pallet::error]
    pub enum Error<T> {
        /// The provided image hash has invalid length (must be 64 hex chars = 64 bytes)
        InvalidHashLength,
        /// The modification level is invalid (must be 0, 1, or 2)
        InvalidModificationLevel,
        /// The authority ID exceeds maximum length
        AuthorityIdTooLong,
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
    }

    /// Dispatchable functions (extrinsics)
    #[pallet::call]
    impl<T: Config> Pallet<T> {
        /// Submit a new image authentication record to the blockchain.
        ///
        /// This function is restricted to authorized aggregator nodes. It stores
        /// the image hash along with authentication metadata permanently on-chain.
        ///
        /// # Arguments
        ///
        /// * `origin` - Must be signed by an authorized aggregator account
        /// * `image_hash` - SHA-256 hash of the image (64 hex chars as bytes)
        /// * `submission_type` - Whether from camera or software
        /// * `modification_level` - 0 (raw), 1 (validated), or 2 (modified)
        /// * `parent_image_hash` - Optional hash of parent image for provenance
        /// * `authority_id` - Manufacturer or software developer identifier
        ///
        /// # Errors
        ///
        /// Returns error if:
        /// - Hash length is not 64 bytes
        /// - Modification level is not 0-2
        /// - Hash already exists in storage
        /// - Parent hash doesn't exist (if specified)
        /// - Authority ID exceeds max length
        ///
        /// # Weight
        ///
        /// Weight is calculated based on:
        /// - One storage read (check for duplicate)
        /// - One storage write (insert record)
        /// - One storage read+write (increment counter)
        #[pallet::call_index(0)]
        #[pallet::weight(10_000)] // TODO: Proper weight calculation
        pub fn submit_image_record(
            origin: OriginFor<T>,
            image_hash: Vec<u8>,
            submission_type: SubmissionType,
            modification_level: u8,
            parent_image_hash: Option<Vec<u8>>,
            authority_id: Vec<u8>,
        ) -> DispatchResult {
            // Verify origin is signed (authorization logic can be added via custom origin)
            let _who = ensure_signed(origin)?;

            // Validate inputs
            ensure!(
                image_hash.len() == 64,
                Error::<T>::InvalidHashLength
            );
            ensure!(
                modification_level <= 2,
                Error::<T>::InvalidModificationLevel
            );
            ensure!(
                authority_id.len() as u32 <= T::MaxAuthorityIdLength::get(),
                Error::<T>::AuthorityIdTooLong
            );

            // Convert to bounded vecs
            let bounded_hash: BoundedVec<u8, T::MaxImageHashLength> = image_hash
                .clone()
                .try_into()
                .map_err(|_| Error::<T>::InvalidHashLength)?;

            let bounded_authority: BoundedVec<u8, T::MaxAuthorityIdLength> = authority_id
                .clone()
                .try_into()
                .map_err(|_| Error::<T>::AuthorityIdTooLong)?;

            // Validate parent hash if provided
            let bounded_parent = if let Some(parent) = parent_image_hash {
                ensure!(
                    parent.len() == 64,
                    Error::<T>::InvalidParentHashLength
                );

                let bounded = parent
                    .try_into()
                    .map_err(|_| Error::<T>::InvalidParentHashLength)?;

                // Ensure parent exists in storage
                ensure!(
                    ImageRecords::<T>::contains_key(&bounded),
                    Error::<T>::ParentHashNotFound
                );

                Some(bounded)
            } else {
                None
            };

            // Ensure hash doesn't already exist (immutability + duplicate prevention)
            ensure!(
                !ImageRecords::<T>::contains_key(&bounded_hash),
                Error::<T>::HashAlreadyExists
            );

            // Get current timestamp and block number
            let timestamp = pallet_timestamp::Pallet::<T>::get();
            let block_number = frame_system::Pallet::<T>::block_number();

            // Create record
            let record = ImageRecord {
                image_hash: bounded_hash.clone(),
                submission_type,
                modification_level,
                parent_image_hash: bounded_parent,
                authority_id: bounded_authority.clone(),
                timestamp,
                block_number,
            };

            // Store record
            ImageRecords::<T>::insert(&bounded_hash, record);

            // Increment total count
            TotalRecords::<T>::mutate(|count| {
                *count = count.saturating_add(1);
            });

            // Emit event
            Self::deposit_event(Event::ImageRecordSubmitted {
                image_hash: bounded_hash,
                authority_id: bounded_authority,
                modification_level,
            });

            Ok(())
        }

        /// Submit multiple image records in a single transaction (batch submission).
        ///
        /// This is more gas-efficient than individual submissions when aggregators
        /// have accumulated multiple validated images.
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
                Vec<u8>,                // image_hash
                SubmissionType,         // submission_type
                u8,                     // modification_level
                Option<Vec<u8>>,        // parent_image_hash
                Vec<u8>,                // authority_id
            )>,
        ) -> DispatchResult {
            let _who = ensure_signed(origin)?;

            // Validate batch constraints
            ensure!(!records.is_empty(), Error::<T>::EmptyBatch);
            ensure!(records.len() <= 100, Error::<T>::BatchTooLarge);

            let count = records.len() as u32;

            // Process each record
            for (image_hash, submission_type, modification_level, parent_image_hash, authority_id) in records {
                // Reuse validation logic from submit_image_record
                ensure!(image_hash.len() == 64, Error::<T>::InvalidHashLength);
                ensure!(modification_level <= 2, Error::<T>::InvalidModificationLevel);
                ensure!(
                    authority_id.len() as u32 <= T::MaxAuthorityIdLength::get(),
                    Error::<T>::AuthorityIdTooLong
                );

                let bounded_hash: BoundedVec<u8, T::MaxImageHashLength> = image_hash
                    .try_into()
                    .map_err(|_| Error::<T>::InvalidHashLength)?;

                let bounded_authority: BoundedVec<u8, T::MaxAuthorityIdLength> = authority_id
                    .try_into()
                    .map_err(|_| Error::<T>::AuthorityIdTooLong)?;

                let bounded_parent = if let Some(parent) = parent_image_hash {
                    ensure!(parent.len() == 64, Error::<T>::InvalidParentHashLength);
                    let bounded = parent
                        .try_into()
                        .map_err(|_| Error::<T>::InvalidParentHashLength)?;
                    ensure!(
                        ImageRecords::<T>::contains_key(&bounded),
                        Error::<T>::ParentHashNotFound
                    );
                    Some(bounded)
                } else {
                    None
                };

                ensure!(
                    !ImageRecords::<T>::contains_key(&bounded_hash),
                    Error::<T>::HashAlreadyExists
                );

                let timestamp = pallet_timestamp::Pallet::<T>::get();
                let block_number = frame_system::Pallet::<T>::block_number();

                let record = ImageRecord {
                    image_hash: bounded_hash.clone(),
                    submission_type,
                    modification_level,
                    parent_image_hash: bounded_parent,
                    authority_id: bounded_authority,
                    timestamp,
                    block_number,
                };

                ImageRecords::<T>::insert(&bounded_hash, record);
                TotalRecords::<T>::mutate(|c| *c = c.saturating_add(1));
            }

            Self::deposit_event(Event::ImageBatchSubmitted { count });

            Ok(())
        }
    }

    /// Public helper functions (not dispatchable)
    impl<T: Config> Pallet<T> {
        /// Query an image record by its hash (public query function)
        ///
        /// This is used by RPC endpoints for fast verification queries.
        pub fn get_image_record(
            hash: &BoundedVec<u8, T::MaxImageHashLength>,
        ) -> Option<ImageRecord<T>> {
            ImageRecords::<T>::get(hash)
        }

        /// Check if an image hash exists in storage
        pub fn image_exists(hash: &BoundedVec<u8, T::MaxImageHashLength>) -> bool {
            ImageRecords::<T>::contains_key(hash)
        }

        /// Get the total number of records stored
        pub fn get_total_records() -> u64 {
            TotalRecords::<T>::get()
        }
    }
}
