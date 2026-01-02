///! Custom RPC implementation for Birthmark node.
///!
///! Provides fast query endpoint for image hash verification.

use std::sync::Arc;
use birthmark_runtime::{opaque::Block, AccountId, Balance, Nonce};
use sc_transaction_pool_api::TransactionPool;
use sp_api::ProvideRuntimeApi;
use sp_block_builder::BlockBuilder;
use sp_blockchain::{Error as BlockChainError, HeaderBackend, HeaderMetadata};
use jsonrpsee::RpcModule;

/// Full RPC dependencies
pub struct FullDeps<C, P> {
    /// The client instance to interact with the blockchain
    pub client: Arc<C>,
    /// Transaction pool instance
    pub pool: Arc<P>,
    /// Whether to deny unsafe calls
    pub deny_unsafe: sc_rpc::DenyUnsafe,
}

/// Instantiate all full RPC extensions
pub fn create_full<C, P>(
    deps: FullDeps<C, P>,
) -> Result<RpcModule<()>, Box<dyn std::error::Error + Send + Sync>>
where
    C: ProvideRuntimeApi<Block>,
    C: HeaderBackend<Block> + HeaderMetadata<Block, Error = BlockChainError> + 'static,
    C: Send + Sync + 'static,
    C::Api: substrate_frame_rpc_system::AccountNonceApi<Block, AccountId, Nonce>,
    C::Api: pallet_transaction_payment_rpc::TransactionPaymentRuntimeApi<Block, Balance>,
    C::Api: BlockBuilder<Block>,
    P: TransactionPool + 'static,
{
    use pallet_transaction_payment_rpc::{TransactionPayment, TransactionPaymentApiServer};
    use substrate_frame_rpc_system::{System, SystemApiServer};

    let mut module = RpcModule::new(());
    let FullDeps {
        client,
        pool,
        deny_unsafe,
    } = deps;

    // Standard Substrate RPC endpoints
    module.merge(System::new(client.clone(), pool, deny_unsafe).into_rpc())?;
    module.merge(TransactionPayment::new(client.clone()).into_rpc())?;

    // TODO: Add custom Birthmark RPC endpoints
    //
    // Example custom RPC for fast image hash queries:
    //
    // module.merge(Birthmark::new(client.clone()).into_rpc())?;
    //
    // This would provide endpoints like:
    // - birthmark_getRecord(image_hash) -> ImageRecord | null
    // - birthmark_getTotalRecords() -> u64
    // - birthmark_verifyImage(image_hash) -> bool
    //
    // Implementation requires:
    // 1. Create pallets/birthmark/rpc crate
    // 2. Define RPC trait with #[rpc(client, server)] macro
    // 3. Implement trait using runtime API calls
    // 4. Merge into module here

    Ok(module)
}

// Custom RPC implementation example (commented out until pallet RPC crate is created)
//
// use birthmark_rpc::{Birthmark, BirthmarkApiServer};
//
// module.merge(Birthmark::new(client.clone()).into_rpc())?;
