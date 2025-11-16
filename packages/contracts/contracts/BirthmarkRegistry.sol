// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BirthmarkRegistry
 * @notice Smart contract for storing and verifying image hash batches on zkSync Era
 * @dev Stores Merkle roots of batched image hashes with access control and pause mechanism
 * @author The Birthmark Standard Foundation
 */
contract BirthmarkRegistry {
    /*//////////////////////////////////////////////////////////////
                            CUSTOM ERRORS
    //////////////////////////////////////////////////////////////*/

    /// @notice Thrown when caller is not authorized
    error Unauthorized();

    /// @notice Thrown when merkle root is zero bytes
    error InvalidMerkleRoot();

    /// @notice Thrown when image count is zero
    error InvalidImageCount();

    /// @notice Thrown when image count exceeds maximum
    error ImageCountTooHigh();

    /// @notice Thrown when contract is paused
    error ContractPaused();

    /// @notice Thrown when batch does not exist
    error BatchDoesNotExist();

    /// @notice Thrown when new owner is zero address
    error InvalidOwner();

    /*//////////////////////////////////////////////////////////////
                                EVENTS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Emitted when a new batch is successfully submitted
     * @param batchId Sequential batch identifier
     * @param merkleRoot Root hash of the Merkle tree containing image hashes
     * @param imageCount Number of images in the batch
     * @param aggregator Address that submitted the batch
     */
    event BatchSubmitted(
        uint256 indexed batchId,
        bytes32 merkleRoot,
        uint32 imageCount,
        address indexed aggregator
    );

    /**
     * @notice Emitted when an aggregator is authorized
     * @param aggregator Address of the authorized aggregator
     */
    event AggregatorAuthorized(address indexed aggregator);

    /**
     * @notice Emitted when an aggregator is revoked
     * @param aggregator Address of the revoked aggregator
     */
    event AggregatorRevoked(address indexed aggregator);

    /**
     * @notice Emitted when ownership is transferred
     * @param previousOwner Address of the previous owner
     * @param newOwner Address of the new owner
     */
    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    /**
     * @notice Emitted when contract is paused
     * @param account Address that paused the contract
     */
    event Paused(address indexed account);

    /**
     * @notice Emitted when contract is unpaused
     * @param account Address that unpaused the contract
     */
    event Unpaused(address indexed account);

    /*//////////////////////////////////////////////////////////////
                            STATE VARIABLES
    //////////////////////////////////////////////////////////////*/

    /// @notice Contract owner address
    address public owner;

    /// @notice Mapping of authorized aggregator addresses
    mapping(address => bool) public authorizedAggregators;

    /// @notice Whether the contract is paused
    bool public paused;

    /// @notice Maximum number of images allowed per batch
    uint32 public constant MAX_IMAGES_PER_BATCH = 10_000;

    /// @notice Next batch ID to be assigned (starts at 1)
    uint256 public nextBatchId = 1;

    /**
     * @notice Batch structure containing Merkle root and metadata
     * @param merkleRoot Root hash of the Merkle tree
     * @param timestamp Block timestamp when batch was submitted
     * @param aggregator Address that submitted the batch
     * @param imageCount Number of images in the batch
     */
    struct Batch {
        bytes32 merkleRoot;
        uint64 timestamp;
        address aggregator;
        uint32 imageCount;
    }

    /// @notice Mapping from batch ID to batch data
    mapping(uint256 => Batch) public batches;

    /*//////////////////////////////////////////////////////////////
                              MODIFIERS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Restricts function to contract owner only
     */
    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    /**
     * @notice Restricts function to authorized aggregators only
     */
    modifier onlyAggregator() {
        if (!authorizedAggregators[msg.sender]) revert Unauthorized();
        _;
    }

    /**
     * @notice Restricts function when contract is not paused
     */
    modifier whenNotPaused() {
        if (paused) revert ContractPaused();
        _;
    }

    /*//////////////////////////////////////////////////////////////
                            CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Initializes the contract with deployer as owner and first aggregator
     * @dev Deployer is automatically authorized as the first aggregator
     */
    constructor() {
        owner = msg.sender;
        authorizedAggregators[msg.sender] = true;
        emit OwnershipTransferred(address(0), msg.sender);
        emit AggregatorAuthorized(msg.sender);
    }

    /*//////////////////////////////////////////////////////////////
                        BATCH SUBMISSION
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Submits a new batch of image hashes as a Merkle root
     * @dev Only authorized aggregators can call this function
     * @param merkleRoot Root hash of the Merkle tree containing image hashes
     * @param imageCount Number of images in the batch (must be 1-10,000)
     * @return batchId The sequential ID assigned to this batch
     */
    function submitBatch(bytes32 merkleRoot, uint32 imageCount)
        external
        onlyAggregator
        whenNotPaused
        returns (uint256 batchId)
    {
        // Validate inputs
        if (merkleRoot == bytes32(0)) revert InvalidMerkleRoot();
        if (imageCount == 0) revert InvalidImageCount();
        if (imageCount > MAX_IMAGES_PER_BATCH) revert ImageCountTooHigh();

        // Assign batch ID and increment counter
        batchId = nextBatchId++;

        // Store batch data
        batches[batchId] = Batch({
            merkleRoot: merkleRoot,
            timestamp: uint64(block.timestamp),
            aggregator: msg.sender,
            imageCount: imageCount
        });

        // Emit event
        emit BatchSubmitted(batchId, merkleRoot, imageCount, msg.sender);

        return batchId;
    }

    /*//////////////////////////////////////////////////////////////
                        BATCH QUERIES
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Retrieves batch information by ID
     * @dev Returns zero values if batch doesn't exist
     * @param batchId The batch ID to query
     * @return merkleRoot The Merkle root of the batch
     * @return timestamp When the batch was submitted
     * @return aggregator Address that submitted the batch
     * @return imageCount Number of images in the batch
     */
    function getBatch(uint256 batchId)
        external
        view
        returns (
            bytes32 merkleRoot,
            uint64 timestamp,
            address aggregator,
            uint32 imageCount
        )
    {
        Batch memory batch = batches[batchId];
        return (
            batch.merkleRoot,
            batch.timestamp,
            batch.aggregator,
            batch.imageCount
        );
    }

    /**
     * @notice Checks if a batch exists
     * @param batchId The batch ID to check
     * @return exists True if the batch exists, false otherwise
     */
    function batchExists(uint256 batchId) external view returns (bool exists) {
        return batches[batchId].timestamp > 0;
    }

    /*//////////////////////////////////////////////////////////////
                        ACCESS CONTROL
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Authorizes a new aggregator
     * @dev Only owner can authorize aggregators
     * @param aggregator Address to authorize
     */
    function authorizeAggregator(address aggregator) external onlyOwner {
        authorizedAggregators[aggregator] = true;
        emit AggregatorAuthorized(aggregator);
    }

    /**
     * @notice Revokes an aggregator's authorization
     * @dev Only owner can revoke aggregators
     * @param aggregator Address to revoke
     */
    function revokeAggregator(address aggregator) external onlyOwner {
        authorizedAggregators[aggregator] = false;
        emit AggregatorRevoked(aggregator);
    }

    /**
     * @notice Transfers contract ownership to a new address
     * @dev Only current owner can transfer ownership
     * @param newOwner Address of the new owner
     */
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert InvalidOwner();
        address previousOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(previousOwner, newOwner);
    }

    /*//////////////////////////////////////////////////////////////
                        PAUSE MECHANISM
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Pauses the contract, preventing batch submissions
     * @dev Only owner can pause. Authorization changes still work when paused.
     */
    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender);
    }

    /**
     * @notice Unpauses the contract, allowing batch submissions
     * @dev Only owner can unpause
     */
    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }
}
