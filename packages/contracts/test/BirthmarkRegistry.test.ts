import { expect } from "chai";
import { Wallet, Provider, Contract } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync-deploy";
import * as hre from "hardhat";

/**
 * Comprehensive test suite for BirthmarkRegistry
 *
 * Coverage:
 * - Deployment and initialization
 * - Batch submission (success and failure cases)
 * - Access control (authorization, revocation, ownership)
 * - Pause mechanism
 * - Batch queries
 * - Edge cases and validation
 */
describe("BirthmarkRegistry", function () {
  let deployer: Wallet;
  let aggregator1: Wallet;
  let aggregator2: Wallet;
  let unauthorized: Wallet;
  let contract: Contract;
  let contractAddress: string;

  // Test data
  const VALID_MERKLE_ROOT =
    "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";
  const VALID_IMAGE_COUNT = 1000;
  const MAX_IMAGE_COUNT = 10000;

  /**
   * Deploy fresh contract before each test
   */
  beforeEach(async function () {
    // Create test wallets
    deployer = Wallet.createRandom();
    aggregator1 = Wallet.createRandom();
    aggregator2 = Wallet.createRandom();
    unauthorized = Wallet.createRandom();

    // Deploy contract using deployer
    const deployerInstance = new Deployer(hre, deployer);
    const artifact = await deployerInstance.loadArtifact("BirthmarkRegistry");
    const deployedContract = await deployerInstance.deploy(artifact, []);
    await deployedContract.waitForDeployment();

    contractAddress = await deployedContract.getAddress();
    contract = deployedContract;
  });

  describe("Deployment", function () {
    it("Should set deployer as owner", async function () {
      const owner = await contract.owner();
      expect(owner).to.equal(deployer.address);
    });

    it("Should authorize deployer as first aggregator", async function () {
      const isAuthorized = await contract.authorizedAggregators(
        deployer.address
      );
      expect(isAuthorized).to.be.true;
    });

    it("Should start with batch ID 1", async function () {
      const nextBatchId = await contract.nextBatchId();
      expect(nextBatchId).to.equal(1);
    });

    it("Should not be paused initially", async function () {
      const isPaused = await contract.paused();
      expect(isPaused).to.be.false;
    });

    it("Should emit OwnershipTransferred event", async function () {
      // Redeploy to capture event
      const deployerInstance = new Deployer(hre, deployer);
      const artifact = await deployerInstance.loadArtifact("BirthmarkRegistry");
      const newContract = await deployerInstance.deploy(artifact, []);

      // Check for event in deployment transaction
      const deployTx = newContract.deploymentTransaction();
      if (!deployTx) {
        throw new Error("No deployment transaction");
      }

      const receipt = await deployTx.wait();
      const events = receipt.logs;

      // Look for OwnershipTransferred event
      expect(events.length).to.be.greaterThan(0);
    });
  });

  describe("Batch Submission", function () {
    it("Should submit batch successfully with valid data", async function () {
      const tx = await contract.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );
      const receipt = await tx.wait();

      expect(receipt.status).to.equal(1);

      // Check batch was stored
      const batch = await contract.getBatch(1);
      expect(batch.merkleRoot).to.equal(VALID_MERKLE_ROOT);
      expect(batch.imageCount).to.equal(VALID_IMAGE_COUNT);
      expect(batch.aggregator).to.equal(deployer.address);
    });

    it("Should emit BatchSubmitted event", async function () {
      const tx = await contract.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );
      const receipt = await tx.wait();

      // Find BatchSubmitted event
      const eventLog = receipt.logs.find((log: any) => {
        try {
          const parsed = contract.interface.parseLog({
            topics: log.topics as string[],
            data: log.data,
          });
          return parsed?.name === "BatchSubmitted";
        } catch {
          return false;
        }
      });

      expect(eventLog).to.not.be.undefined;
    });

    it("Should increment batch ID sequentially", async function () {
      await contract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT);
      await contract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT);
      await contract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT);

      const nextBatchId = await contract.nextBatchId();
      expect(nextBatchId).to.equal(4); // Started at 1, three batches submitted
    });

    it("Should revert when merkle root is zero", async function () {
      const ZERO_MERKLE_ROOT =
        "0x0000000000000000000000000000000000000000000000000000000000000000";

      await expect(
        contract.submitBatch(ZERO_MERKLE_ROOT, VALID_IMAGE_COUNT)
      ).to.be.revertedWithCustomError(contract, "InvalidMerkleRoot");
    });

    it("Should revert when image count is zero", async function () {
      await expect(
        contract.submitBatch(VALID_MERKLE_ROOT, 0)
      ).to.be.revertedWithCustomError(contract, "InvalidImageCount");
    });

    it("Should revert when image count exceeds maximum", async function () {
      await expect(
        contract.submitBatch(VALID_MERKLE_ROOT, MAX_IMAGE_COUNT + 1)
      ).to.be.revertedWithCustomError(contract, "ImageCountTooHigh");
    });

    it("Should accept maximum image count", async function () {
      const tx = await contract.submitBatch(VALID_MERKLE_ROOT, MAX_IMAGE_COUNT);
      const receipt = await tx.wait();
      expect(receipt.status).to.equal(1);
    });

    it("Should accept image count of 1", async function () {
      const tx = await contract.submitBatch(VALID_MERKLE_ROOT, 1);
      const receipt = await tx.wait();
      expect(receipt.status).to.equal(1);

      const batch = await contract.getBatch(1);
      expect(batch.imageCount).to.equal(1);
    });

    it("Should revert when caller is not authorized", async function () {
      const unauthorizedContract = contract.connect(unauthorized) as Contract;

      await expect(
        unauthorizedContract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT)
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });

    it("Should revert when contract is paused", async function () {
      await contract.pause();

      await expect(
        contract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT)
      ).to.be.revertedWithCustomError(contract, "ContractPaused");
    });

    it("Should store correct timestamp", async function () {
      const tx = await contract.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );
      await tx.wait();

      const batch = await contract.getBatch(1);
      expect(batch.timestamp).to.be.greaterThan(0);
    });
  });

  describe("Batch Queries", function () {
    beforeEach(async function () {
      // Submit a test batch
      await contract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT);
    });

    it("Should return correct batch data", async function () {
      const batch = await contract.getBatch(1);

      expect(batch.merkleRoot).to.equal(VALID_MERKLE_ROOT);
      expect(batch.imageCount).to.equal(VALID_IMAGE_COUNT);
      expect(batch.aggregator).to.equal(deployer.address);
      expect(batch.timestamp).to.be.greaterThan(0);
    });

    it("Should return zero values for non-existent batch", async function () {
      const batch = await contract.getBatch(999);

      expect(batch.merkleRoot).to.equal(
        "0x0000000000000000000000000000000000000000000000000000000000000000"
      );
      expect(batch.imageCount).to.equal(0);
      expect(batch.timestamp).to.equal(0);
    });

    it("Should correctly identify if batch exists", async function () {
      const exists = await contract.batchExists(1);
      const notExists = await contract.batchExists(999);

      expect(exists).to.be.true;
      expect(notExists).to.be.false;
    });

    it("Should handle multiple batches", async function () {
      const merkleRoot2 =
        "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890";
      await contract.submitBatch(merkleRoot2, 2000);

      const batch1 = await contract.getBatch(1);
      const batch2 = await contract.getBatch(2);

      expect(batch1.merkleRoot).to.equal(VALID_MERKLE_ROOT);
      expect(batch1.imageCount).to.equal(VALID_IMAGE_COUNT);
      expect(batch2.merkleRoot).to.equal(merkleRoot2);
      expect(batch2.imageCount).to.equal(2000);
    });
  });

  describe("Access Control - Aggregator Authorization", function () {
    it("Should authorize new aggregator", async function () {
      await contract.authorizeAggregator(aggregator1.address);

      const isAuthorized = await contract.authorizedAggregators(
        aggregator1.address
      );
      expect(isAuthorized).to.be.true;
    });

    it("Should emit AggregatorAuthorized event", async function () {
      const tx = await contract.authorizeAggregator(aggregator1.address);
      const receipt = await tx.wait();

      const eventLog = receipt.logs.find((log: any) => {
        try {
          const parsed = contract.interface.parseLog({
            topics: log.topics as string[],
            data: log.data,
          });
          return parsed?.name === "AggregatorAuthorized";
        } catch {
          return false;
        }
      });

      expect(eventLog).to.not.be.undefined;
    });

    it("Should allow authorized aggregator to submit batches", async function () {
      await contract.authorizeAggregator(aggregator1.address);

      const aggregatorContract = contract.connect(aggregator1) as Contract;
      const tx = await aggregatorContract.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );
      const receipt = await tx.wait();

      expect(receipt.status).to.equal(1);
    });

    it("Should revert when non-owner tries to authorize", async function () {
      const unauthorizedContract = contract.connect(unauthorized) as Contract;

      await expect(
        unauthorizedContract.authorizeAggregator(aggregator1.address)
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });

    it("Should revoke aggregator authorization", async function () {
      await contract.authorizeAggregator(aggregator1.address);
      await contract.revokeAggregator(aggregator1.address);

      const isAuthorized = await contract.authorizedAggregators(
        aggregator1.address
      );
      expect(isAuthorized).to.be.false;
    });

    it("Should emit AggregatorRevoked event", async function () {
      await contract.authorizeAggregator(aggregator1.address);
      const tx = await contract.revokeAggregator(aggregator1.address);
      const receipt = await tx.wait();

      const eventLog = receipt.logs.find((log: any) => {
        try {
          const parsed = contract.interface.parseLog({
            topics: log.topics as string[],
            data: log.data,
          });
          return parsed?.name === "AggregatorRevoked";
        } catch {
          return false;
        }
      });

      expect(eventLog).to.not.be.undefined;
    });

    it("Should prevent revoked aggregator from submitting", async function () {
      await contract.authorizeAggregator(aggregator1.address);
      await contract.revokeAggregator(aggregator1.address);

      const aggregatorContract = contract.connect(aggregator1) as Contract;

      await expect(
        aggregatorContract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT)
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });

    it("Should revert when non-owner tries to revoke", async function () {
      const unauthorizedContract = contract.connect(unauthorized) as Contract;

      await expect(
        unauthorizedContract.revokeAggregator(aggregator1.address)
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });
  });

  describe("Access Control - Ownership", function () {
    it("Should transfer ownership successfully", async function () {
      await contract.transferOwnership(aggregator1.address);

      const newOwner = await contract.owner();
      expect(newOwner).to.equal(aggregator1.address);
    });

    it("Should emit OwnershipTransferred event", async function () {
      const tx = await contract.transferOwnership(aggregator1.address);
      const receipt = await tx.wait();

      const eventLog = receipt.logs.find((log: any) => {
        try {
          const parsed = contract.interface.parseLog({
            topics: log.topics as string[],
            data: log.data,
          });
          return parsed?.name === "OwnershipTransferred";
        } catch {
          return false;
        }
      });

      expect(eventLog).to.not.be.undefined;
    });

    it("Should allow new owner to perform owner actions", async function () {
      await contract.transferOwnership(aggregator1.address);

      const newOwnerContract = contract.connect(aggregator1) as Contract;
      const tx = await newOwnerContract.authorizeAggregator(
        aggregator2.address
      );
      const receipt = await tx.wait();

      expect(receipt.status).to.equal(1);
    });

    it("Should prevent old owner from performing owner actions", async function () {
      await contract.transferOwnership(aggregator1.address);

      await expect(
        contract.authorizeAggregator(aggregator2.address)
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });

    it("Should revert when transferring to zero address", async function () {
      await expect(
        contract.transferOwnership(hre.ethers.ZeroAddress)
      ).to.be.revertedWithCustomError(contract, "InvalidOwner");
    });

    it("Should revert when non-owner tries to transfer", async function () {
      const unauthorizedContract = contract.connect(unauthorized) as Contract;

      await expect(
        unauthorizedContract.transferOwnership(aggregator1.address)
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });
  });

  describe("Pause Mechanism", function () {
    it("Should pause contract successfully", async function () {
      await contract.pause();

      const isPaused = await contract.paused();
      expect(isPaused).to.be.true;
    });

    it("Should emit Paused event", async function () {
      const tx = await contract.pause();
      const receipt = await tx.wait();

      const eventLog = receipt.logs.find((log: any) => {
        try {
          const parsed = contract.interface.parseLog({
            topics: log.topics as string[],
            data: log.data,
          });
          return parsed?.name === "Paused";
        } catch {
          return false;
        }
      });

      expect(eventLog).to.not.be.undefined;
    });

    it("Should unpause contract successfully", async function () {
      await contract.pause();
      await contract.unpause();

      const isPaused = await contract.paused();
      expect(isPaused).to.be.false;
    });

    it("Should emit Unpaused event", async function () {
      await contract.pause();
      const tx = await contract.unpause();
      const receipt = await tx.wait();

      const eventLog = receipt.logs.find((log: any) => {
        try {
          const parsed = contract.interface.parseLog({
            topics: log.topics as string[],
            data: log.data,
          });
          return parsed?.name === "Unpaused";
        } catch {
          return false;
        }
      });

      expect(eventLog).to.not.be.undefined;
    });

    it("Should block batch submission when paused", async function () {
      await contract.pause();

      await expect(
        contract.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT)
      ).to.be.revertedWithCustomError(contract, "ContractPaused");
    });

    it("Should allow batch submission after unpause", async function () {
      await contract.pause();
      await contract.unpause();

      const tx = await contract.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );
      const receipt = await tx.wait();
      expect(receipt.status).to.equal(1);
    });

    it("Should allow authorization changes when paused", async function () {
      await contract.pause();

      const tx = await contract.authorizeAggregator(aggregator1.address);
      const receipt = await tx.wait();
      expect(receipt.status).to.equal(1);

      const isAuthorized = await contract.authorizedAggregators(
        aggregator1.address
      );
      expect(isAuthorized).to.be.true;
    });

    it("Should revert when non-owner tries to pause", async function () {
      const unauthorizedContract = contract.connect(unauthorized) as Contract;

      await expect(
        unauthorizedContract.pause()
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });

    it("Should revert when non-owner tries to unpause", async function () {
      await contract.pause();

      const unauthorizedContract = contract.connect(unauthorized) as Contract;

      await expect(
        unauthorizedContract.unpause()
      ).to.be.revertedWithCustomError(contract, "Unauthorized");
    });
  });

  describe("Multiple Aggregators", function () {
    beforeEach(async function () {
      await contract.authorizeAggregator(aggregator1.address);
      await contract.authorizeAggregator(aggregator2.address);
    });

    it("Should allow multiple aggregators to submit batches", async function () {
      const contract1 = contract.connect(aggregator1) as Contract;
      const contract2 = contract.connect(aggregator2) as Contract;

      const tx1 = await contract1.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );
      const tx2 = await contract2.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );

      const receipt1 = await tx1.wait();
      const receipt2 = await tx2.wait();

      expect(receipt1.status).to.equal(1);
      expect(receipt2.status).to.equal(1);
    });

    it("Should track which aggregator submitted each batch", async function () {
      const contract1 = contract.connect(aggregator1) as Contract;
      const contract2 = contract.connect(aggregator2) as Contract;

      await contract1.submitBatch(VALID_MERKLE_ROOT, VALID_IMAGE_COUNT);
      await contract2.submitBatch(VALID_MERKLE_ROOT, 2000);

      const batch1 = await contract.getBatch(1);
      const batch2 = await contract.getBatch(2);

      expect(batch1.aggregator).to.equal(aggregator1.address);
      expect(batch2.aggregator).to.equal(aggregator2.address);
    });
  });

  describe("Gas Usage", function () {
    it("Should report gas for batch submission", async function () {
      const tx = await contract.submitBatch(
        VALID_MERKLE_ROOT,
        VALID_IMAGE_COUNT
      );
      const receipt = await tx.wait();

      console.log(`      ⛽ Gas used for submitBatch: ${receipt.gasUsed}`);
      expect(receipt.gasUsed).to.be.greaterThan(0);
    });

    it("Should report gas for authorization", async function () {
      const tx = await contract.authorizeAggregator(aggregator1.address);
      const receipt = await tx.wait();

      console.log(
        `      ⛽ Gas used for authorizeAggregator: ${receipt.gasUsed}`
      );
      expect(receipt.gasUsed).to.be.greaterThan(0);
    });
  });
});
