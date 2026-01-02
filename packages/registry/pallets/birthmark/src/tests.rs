use crate::{self as pallet_birthmark, *};
use frame_support::{
    assert_noop, assert_ok, derive_impl, parameter_types,
    traits::{ConstU32, ConstU64},
};
use sp_runtime::{traits::IdentityLookup, BuildStorage};

type Block = frame_system::mocking::MockBlock<Test>;

// Configure a mock runtime to test the pallet
frame_support::construct_runtime!(
    pub enum Test
    {
        System: frame_system,
        Timestamp: pallet_timestamp,
        Birthmark: pallet_birthmark,
    }
);

#[derive_impl(frame_system::config_preludes::TestDefaultConfig)]
impl frame_system::Config for Test {
    type Block = Block;
    type AccountId = u64;
    type Lookup = IdentityLookup<Self::AccountId>;
}

impl pallet_timestamp::Config for Test {
    type Moment = u64;
    type OnTimestampSet = ();
    type MinimumPeriod = ConstU64<5>;
    type WeightInfo = ();
}

parameter_types! {
    pub const MaxAuthorityIdLength: u32 = 100;
    pub const MaxImageHashLength: u32 = 64;
}

impl pallet_birthmark::Config for Test {
    type RuntimeEvent = RuntimeEvent;
    type MaxAuthorityIdLength = MaxAuthorityIdLength;
    type MaxImageHashLength = MaxImageHashLength;
}

// Helper function to create new test externalities
pub fn new_test_ext() -> sp_io::TestExternalities {
    let t = frame_system::GenesisConfig::<Test>::default()
        .build_storage()
        .unwrap();
    let mut ext = sp_io::TestExternalities::new(t);
    ext.execute_with(|| {
        // Set block number and timestamp to avoid zero values
        System::set_block_number(1);
        Timestamp::set_timestamp(12345);
    });
    ext
}

// Helper to create a test image hash
fn test_hash(id: u8) -> Vec<u8> {
    let mut hash = vec![id; 64];
    hash
}

#[test]
fn submit_image_record_works() {
    new_test_ext().execute_with(|| {
        let hash = test_hash(1);
        let authority_id = b"CANON_EOS_R5".to_vec();

        // Submit a camera record
        assert_ok!(Birthmark::submit_image_record(
            RuntimeOrigin::signed(1),
            hash.clone(),
            SubmissionType::Camera,
            0, // modification_level: raw
            None, // no parent
            authority_id.clone(),
        ));

        // Verify record was stored
        let bounded_hash: BoundedVec<u8, ConstU32<64>> = hash.try_into().unwrap();
        let record = Birthmark::image_records(&bounded_hash).unwrap();
        assert_eq!(record.modification_level, 0);
        assert_eq!(record.parent_image_hash, None);

        // Verify total count increased
        assert_eq!(Birthmark::total_records(), 1);

        // Verify event was emitted
        System::assert_last_event(
            Event::ImageRecordSubmitted {
                image_hash: bounded_hash,
                authority_id: authority_id.try_into().unwrap(),
                modification_level: 0,
            }
            .into(),
        );
    });
}

#[test]
fn duplicate_hash_fails() {
    new_test_ext().execute_with(|| {
        let hash = test_hash(2);
        let authority_id = b"SONY_A7IV".to_vec();

        // Submit first record
        assert_ok!(Birthmark::submit_image_record(
            RuntimeOrigin::signed(1),
            hash.clone(),
            SubmissionType::Camera,
            0,
            None,
            authority_id.clone(),
        ));

        // Attempt duplicate submission
        assert_noop!(
            Birthmark::submit_image_record(
                RuntimeOrigin::signed(1),
                hash.clone(),
                SubmissionType::Camera,
                0,
                None,
                authority_id,
            ),
            Error::<Test>::HashAlreadyExists
        );

        // Verify count is still 1
        assert_eq!(Birthmark::total_records(), 1);
    });
}

#[test]
fn invalid_hash_length_fails() {
    new_test_ext().execute_with(|| {
        let short_hash = vec![1u8; 32]; // Only 32 bytes instead of 64
        let authority_id = b"TEST_CAMERA".to_vec();

        assert_noop!(
            Birthmark::submit_image_record(
                RuntimeOrigin::signed(1),
                short_hash,
                SubmissionType::Camera,
                0,
                None,
                authority_id,
            ),
            Error::<Test>::InvalidHashLength
        );
    });
}

#[test]
fn invalid_modification_level_fails() {
    new_test_ext().execute_with(|| {
        let hash = test_hash(3);
        let authority_id = b"TEST_CAMERA".to_vec();

        assert_noop!(
            Birthmark::submit_image_record(
                RuntimeOrigin::signed(1),
                hash,
                SubmissionType::Camera,
                3, // Invalid: must be 0, 1, or 2
                None,
                authority_id,
            ),
            Error::<Test>::InvalidModificationLevel
        );
    });
}

#[test]
fn provenance_chain_works() {
    new_test_ext().execute_with(|| {
        let raw_hash = test_hash(10);
        let processed_hash = test_hash(11);
        let authority_id = b"NIKON_Z9".to_vec();

        // Submit raw sensor data (parent of provenance chain)
        assert_ok!(Birthmark::submit_image_record(
            RuntimeOrigin::signed(1),
            raw_hash.clone(),
            SubmissionType::Camera,
            0, // raw
            None,
            authority_id.clone(),
        ));

        // Submit processed image with raw as parent
        assert_ok!(Birthmark::submit_image_record(
            RuntimeOrigin::signed(1),
            processed_hash.clone(),
            SubmissionType::Camera,
            1, // validated/processed
            Some(raw_hash.clone()),
            authority_id,
        ));

        // Verify provenance chain
        let bounded_processed: BoundedVec<u8, ConstU32<64>> = processed_hash.try_into().unwrap();
        let record = Birthmark::image_records(&bounded_processed).unwrap();
        assert_eq!(record.modification_level, 1);
        assert!(record.parent_image_hash.is_some());

        let bounded_raw: BoundedVec<u8, ConstU32<64>> = raw_hash.try_into().unwrap();
        assert_eq!(record.parent_image_hash, Some(bounded_raw));

        // Verify total count
        assert_eq!(Birthmark::total_records(), 2);
    });
}

#[test]
fn parent_hash_must_exist() {
    new_test_ext().execute_with(|| {
        let hash = test_hash(20);
        let nonexistent_parent = test_hash(99);
        let authority_id = b"TEST_CAMERA".to_vec();

        // Try to submit with non-existent parent
        assert_noop!(
            Birthmark::submit_image_record(
                RuntimeOrigin::signed(1),
                hash,
                SubmissionType::Camera,
                1,
                Some(nonexistent_parent),
                authority_id,
            ),
            Error::<Test>::ParentHashNotFound
        );
    });
}

#[test]
fn software_submission_works() {
    new_test_ext().execute_with(|| {
        let hash = test_hash(30);
        let authority_id = b"ADOBE_PHOTOSHOP".to_vec();

        assert_ok!(Birthmark::submit_image_record(
            RuntimeOrigin::signed(1),
            hash.clone(),
            SubmissionType::Software,
            2, // modified
            None,
            authority_id,
        ));

        let bounded_hash: BoundedVec<u8, ConstU32<64>> = hash.try_into().unwrap();
        let record = Birthmark::image_records(&bounded_hash).unwrap();
        assert!(matches!(record.submission_type, SubmissionType::Software));
        assert_eq!(record.modification_level, 2);
    });
}

#[test]
fn batch_submission_works() {
    new_test_ext().execute_with(|| {
        let authority_id = b"BATCH_CAMERA".to_vec();

        let records = vec![
            (
                test_hash(40),
                SubmissionType::Camera,
                0,
                None,
                authority_id.clone(),
            ),
            (
                test_hash(41),
                SubmissionType::Camera,
                0,
                None,
                authority_id.clone(),
            ),
            (
                test_hash(42),
                SubmissionType::Camera,
                0,
                None,
                authority_id.clone(),
            ),
        ];

        assert_ok!(Birthmark::submit_image_batch(
            RuntimeOrigin::signed(1),
            records,
        ));

        // Verify all records were stored
        assert_eq!(Birthmark::total_records(), 3);

        // Verify event
        System::assert_last_event(Event::ImageBatchSubmitted { count: 3 }.into());
    });
}

#[test]
fn empty_batch_fails() {
    new_test_ext().execute_with(|| {
        assert_noop!(
            Birthmark::submit_image_batch(RuntimeOrigin::signed(1), vec![]),
            Error::<Test>::EmptyBatch
        );
    });
}

#[test]
fn batch_too_large_fails() {
    new_test_ext().execute_with(|| {
        let authority_id = b"TEST".to_vec();
        let mut records = Vec::new();

        // Create 101 records (exceeds max of 100)
        for i in 0..101 {
            records.push((
                test_hash(i as u8),
                SubmissionType::Camera,
                0,
                None,
                authority_id.clone(),
            ));
        }

        assert_noop!(
            Birthmark::submit_image_batch(RuntimeOrigin::signed(1), records),
            Error::<Test>::BatchTooLarge
        );
    });
}

#[test]
fn helper_functions_work() {
    new_test_ext().execute_with(|| {
        let hash = test_hash(50);
        let authority_id = b"HELPER_TEST".to_vec();

        // Initially doesn't exist
        let bounded_hash: BoundedVec<u8, ConstU32<64>> = hash.clone().try_into().unwrap();
        assert!(!Birthmark::image_exists(&bounded_hash));
        assert_eq!(Birthmark::get_image_record(&bounded_hash), None);

        // Submit record
        assert_ok!(Birthmark::submit_image_record(
            RuntimeOrigin::signed(1),
            hash.clone(),
            SubmissionType::Camera,
            0,
            None,
            authority_id,
        ));

        // Now exists
        assert!(Birthmark::image_exists(&bounded_hash));
        assert!(Birthmark::get_image_record(&bounded_hash).is_some());

        // Total count updated
        assert_eq!(Birthmark::get_total_records(), 1);
    });
}
