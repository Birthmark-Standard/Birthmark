import { Wallet, Provider, Contract } from "zksync-ethers";
import * as hre from "hardhat";
import * as dotenv from "dotenv";

dotenv.config();

/**
 * Authorizes a new aggregator address to submit batches
 *
 * Usage:
 *   npm run authorize -- 0x1234...5678
 *
 * Prerequisites:
 * 1. CONTRACT_ADDRESS set in .env file
 * 2. PRIVATE_KEY (owner wallet) set in .env file
 * 3. Owner wallet funded with gas
 */
async function main() {
  console.log("🔑 Authorizing new aggregator...\n");

  // Get aggregator address from command line
  const aggregatorAddress = process.argv[2];

  if (!aggregatorAddress) {
    throw new Error(
      "❌ No aggregator address provided.\n" +
      "Usage: npm run authorize -- <AGGREGATOR_ADDRESS>"
    );
  }

  // Validate address format
  if (!hre.ethers.isAddress(aggregatorAddress)) {
    throw new Error(`❌ Invalid Ethereum address: ${aggregatorAddress}`);
  }

  console.log(`📍 Aggregator to authorize: ${aggregatorAddress}`);

  // Check for required environment variables
  if (!process.env.PRIVATE_KEY) {
    throw new Error("❌ PRIVATE_KEY not found in .env file");
  }

  if (!process.env.CONTRACT_ADDRESS) {
    throw new Error("❌ CONTRACT_ADDRESS not found in .env file");
  }

  // Initialize wallet
  const wallet = new Wallet(process.env.PRIVATE_KEY);
  console.log(`👤 Owner address: ${wallet.address}`);

  // Connect to zkSync provider
  const provider = new Provider(
    process.env.ZKSYNC_RPC_URL || "https://sepolia.era.zksync.dev"
  );
  const connectedWallet = wallet.connect(provider);

  // Check balance
  const balance = await connectedWallet.getBalance();
  console.log(`💰 Owner balance: ${hre.ethers.formatEther(balance)} ETH`);

  if (balance === 0n) {
    throw new Error("❌ Owner wallet has zero balance for gas");
  }

  // Load contract
  const contractAddress = process.env.CONTRACT_ADDRESS;
  const contract = new Contract(
    contractAddress,
    [
      "function owner() view returns (address)",
      "function authorizedAggregators(address) view returns (bool)",
      "function authorizeAggregator(address aggregator)",
      "event AggregatorAuthorized(address indexed aggregator)",
    ],
    connectedWallet
  );

  console.log(`📍 Contract address: ${contractAddress}`);

  // Verify we're the owner
  const owner = await contract.owner();
  if (owner.toLowerCase() !== wallet.address.toLowerCase()) {
    throw new Error(
      `❌ Not authorized. Current owner: ${owner}, Your address: ${wallet.address}`
    );
  }

  console.log("✅ Owner verification passed");

  // Check if already authorized
  const isAlreadyAuthorized = await contract.authorizedAggregators(
    aggregatorAddress
  );

  if (isAlreadyAuthorized) {
    console.log(`\n⚠️  Address ${aggregatorAddress} is already authorized`);
    console.log("No transaction needed.");
    process.exit(0);
  }

  // Send authorization transaction
  console.log("\n⏳ Sending authorization transaction...");
  const tx = await contract.authorizeAggregator(aggregatorAddress);

  console.log(`📦 Transaction hash: ${tx.hash}`);
  console.log("⏳ Waiting for confirmation...");

  const receipt = await tx.wait();

  if (receipt.status === 1) {
    console.log("\n✅ Aggregator authorized successfully!");
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log(`📍 Aggregator: ${aggregatorAddress}`);
    console.log(`📦 Transaction: ${tx.hash}`);
    console.log(`⛽ Gas used: ${receipt.gasUsed.toString()}`);
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // Verify authorization
    const isNowAuthorized = await contract.authorizedAggregators(
      aggregatorAddress
    );
    console.log(`\n🔍 Verification: Authorized = ${isNowAuthorized}`);
  } else {
    throw new Error("❌ Transaction failed");
  }
}

// Execute script
main()
  .then(() => {
    console.log("\n✅ Authorization script completed successfully!");
    process.exit(0);
  })
  .catch((error) => {
    console.error("\n❌ Authorization failed:");
    console.error(error);
    process.exit(1);
  });
