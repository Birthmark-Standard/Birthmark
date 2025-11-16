import { Wallet } from "zksync-ethers";
import { Deployer } from "@matterlabs/hardhat-zksync-deploy";
import * as hre from "hardhat";
import * as dotenv from "dotenv";

dotenv.config();

/**
 * Deploys the BirthmarkRegistry contract to zkSync Era
 *
 * Prerequisites:
 * 1. PRIVATE_KEY set in .env file
 * 2. Deployer wallet funded with testnet ETH
 * 3. ZKSYNC_RPC_URL configured in .env (or uses default)
 *
 * The deployer becomes the contract owner and first authorized aggregator.
 */
async function main() {
  console.log("🚀 Deploying BirthmarkRegistry to zkSync Era...\n");

  // Check for private key
  if (!process.env.PRIVATE_KEY) {
    throw new Error(
      "❌ PRIVATE_KEY not found in environment variables.\n" +
      "Please copy .env.example to .env and add your private key."
    );
  }

  // Initialize wallet
  const wallet = new Wallet(process.env.PRIVATE_KEY);
  console.log(`📍 Deployer address: ${wallet.address}`);

  // Create deployer instance
  const deployer = new Deployer(hre, wallet);

  // Load contract artifact
  const artifact = await deployer.loadArtifact("BirthmarkRegistry");
  console.log(`📄 Contract artifact loaded: ${artifact.contractName}`);

  // Check deployer balance
  const balance = await wallet.getBalance();
  console.log(`💰 Deployer balance: ${hre.ethers.formatEther(balance)} ETH`);

  if (balance === 0n) {
    throw new Error(
      "❌ Deployer wallet has zero balance.\n" +
      "Get testnet ETH from: https://portal.zksync.io/faucet"
    );
  }

  // Deploy contract
  console.log("\n⏳ Deploying contract...");
  const contract = await deployer.deploy(artifact, []);

  console.log(`✅ Contract deployed successfully!`);
  console.log(`📍 Contract address: ${await contract.getAddress()}`);

  // Wait for deployment to be indexed
  console.log("\n⏳ Waiting for deployment to be indexed...");
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();

  // Verify owner and authorization
  const owner = await contract.owner();
  const isAuthorized = await contract.authorizedAggregators(wallet.address);

  console.log("\n✅ Deployment complete!");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log(`📍 Contract Address: ${contractAddress}`);
  console.log(`👤 Owner: ${owner}`);
  console.log(`🔑 Deployer Authorized: ${isAuthorized}`);
  console.log(`🌐 Network: ${hre.network.name}`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

  // Get transaction details
  const deployTx = contract.deploymentTransaction();
  if (deployTx) {
    console.log(`\n📦 Transaction hash: ${deployTx.hash}`);
  }

  // Explorer link
  const explorerUrl = getExplorerUrl(hre.network.name, contractAddress);
  if (explorerUrl) {
    console.log(`\n🔍 View on explorer: ${explorerUrl}`);
  }

  // Next steps
  console.log("\n📝 Next steps:");
  console.log("1. Save the contract address to your .env file:");
  console.log(`   CONTRACT_ADDRESS=${contractAddress}`);
  console.log("\n2. Verify the contract (optional):");
  console.log(`   npx hardhat verify --network ${hre.network.name} ${contractAddress}`);
  console.log("\n3. Authorize additional aggregators:");
  console.log("   npm run authorize -- <AGGREGATOR_ADDRESS>");

  return contractAddress;
}

/**
 * Gets the block explorer URL for a contract address
 */
function getExplorerUrl(network: string, address: string): string | null {
  const explorers: { [key: string]: string } = {
    zkSyncTestnet: "https://sepolia.explorer.zksync.io/address",
    zkSyncMainnet: "https://explorer.zksync.io/address",
  };

  const baseUrl = explorers[network];
  return baseUrl ? `${baseUrl}/${address}` : null;
}

// Execute deployment
main()
  .then((address) => {
    console.log(`\n✅ Deployment script completed successfully!`);
    process.exit(0);
  })
  .catch((error) => {
    console.error("\n❌ Deployment failed:");
    console.error(error);
    process.exit(1);
  });
