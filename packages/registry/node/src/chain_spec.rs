use birthmark_runtime::{
    AccountId, AuraConfig, BalancesConfig, GenesisConfig, GrandpaConfig, Signature,
    SudoConfig, SystemConfig, WASM_BINARY, RuntimeGenesisConfig,
};
use sc_service::ChainType;
use sp_consensus_aura::sr25519::AuthorityId as AuraId;
use sp_consensus_grandpa::AuthorityId as GrandpaId;
use sp_core::{sr25519, Pair, Public};
use sp_runtime::traits::{IdentifyAccount, Verify};

// The URL for the telemetry server
// const STAGING_TELEMETRY_URL: &str = "wss://telemetry.polkadot.io/submit/";

/// Specialized `ChainSpec`. This is a specialization of the general Substrate ChainSpec type.
pub type ChainSpec = sc_service::GenericChainSpec<RuntimeGenesisConfig>;

/// Generate a crypto pair from seed
pub fn get_from_seed<TPublic: Public>(seed: &str) -> <TPublic::Pair as Pair>::Public {
    TPublic::Pair::from_string(&format!("//{}", seed), None)
        .expect("static values are valid; qed")
        .public()
}

type AccountPublic = <Signature as Verify>::Signer;

/// Generate an account ID from seed
pub fn get_account_id_from_seed<TPublic: Public>(seed: &str) -> AccountId
where
    AccountPublic: From<<TPublic::Pair as Pair>::Public>,
{
    AccountPublic::from(get_from_seed::<TPublic>(seed)).into_account()
}

/// Generate an Aura authority key
pub fn authority_keys_from_seed(s: &str) -> (AuraId, GrandpaId) {
    (get_from_seed::<AuraId>(s), get_from_seed::<GrandpaId>(s))
}

/// Development chain configuration
pub fn development_config() -> Result<ChainSpec, String> {
    Ok(ChainSpec::builder(
        WASM_BINARY.ok_or_else(|| "Development wasm not available".to_string())?,
        None,
    )
    .with_name("Birthmark Development")
    .with_id("birthmark_dev")
    .with_chain_type(ChainType::Development)
    .with_genesis_config_patch(testnet_genesis(
        // Initial PoA authorities (validators)
        vec![authority_keys_from_seed("Alice")],
        // Sudo account
        get_account_id_from_seed::<sr25519::Public>("Alice"),
        // Pre-funded accounts
        vec![
            get_account_id_from_seed::<sr25519::Public>("Alice"),
            get_account_id_from_seed::<sr25519::Public>("Bob"),
            get_account_id_from_seed::<sr25519::Public>("Charlie"),
            get_account_id_from_seed::<sr25519::Public>("Dave"),
            get_account_id_from_seed::<sr25519::Public>("Eve"),
            get_account_id_from_seed::<sr25519::Public>("Ferdie"),
            get_account_id_from_seed::<sr25519::Public>("Alice//stash"),
            get_account_id_from_seed::<sr25519::Public>("Bob//stash"),
        ],
        true,
    ))
    .build())
}

/// Local testnet configuration (multi-validator)
pub fn local_testnet_config() -> Result<ChainSpec, String> {
    Ok(ChainSpec::builder(
        WASM_BINARY.ok_or_else(|| "Development wasm not available".to_string())?,
        None,
    )
    .with_name("Birthmark Local Testnet")
    .with_id("birthmark_local")
    .with_chain_type(ChainType::Local)
    .with_genesis_config_patch(testnet_genesis(
        // Initial PoA authorities (validators) - simulates journalism coalition
        vec![
            authority_keys_from_seed("Alice"),
            authority_keys_from_seed("Bob"),
            authority_keys_from_seed("Charlie"),
        ],
        // Sudo account
        get_account_id_from_seed::<sr25519::Public>("Alice"),
        // Pre-funded accounts
        vec![
            get_account_id_from_seed::<sr25519::Public>("Alice"),
            get_account_id_from_seed::<sr25519::Public>("Bob"),
            get_account_id_from_seed::<sr25519::Public>("Charlie"),
            get_account_id_from_seed::<sr25519::Public>("Dave"),
        ],
        true,
    ))
    .build())
}

/// Production chain configuration template
///
/// In production, validator keys should be generated securely and distributed
/// to journalism organizations. This template shows the structure.
pub fn production_config() -> Result<ChainSpec, String> {
    Ok(ChainSpec::builder(
        WASM_BINARY.ok_or_else(|| "Production wasm not available".to_string())?,
        None,
    )
    .with_name("Birthmark Media Registry")
    .with_id("birthmark_mainnet")
    .with_chain_type(ChainType::Live)
    .with_genesis_config_patch(testnet_genesis(
        // TODO: Replace with actual validator keys from journalism orgs
        // Example structure for production:
        // vec![
        //     (nppa_aura_key, nppa_grandpa_key),
        //     (ifcn_aura_key, ifcn_grandpa_key),
        //     (cpj_aura_key, cpj_grandpa_key),
        //     // ... up to 50 validators
        // ],
        vec![authority_keys_from_seed("ProductionValidator1")],
        // TODO: Set to governance-controlled sudo account or remove sudo entirely
        get_account_id_from_seed::<sr25519::Public>("GovernanceAccount"),
        // Pre-funded accounts for initial gas (journalism orgs)
        vec![
            get_account_id_from_seed::<sr25519::Public>("NPPA"),
            get_account_id_from_seed::<sr25519::Public>("IFCN"),
            get_account_id_from_seed::<sr25519::Public>("CPJ"),
        ],
        false, // Do not include sudo in production
    ))
    .build())
}

/// Configure initial storage state for FRAME modules
fn testnet_genesis(
    initial_authorities: Vec<(AuraId, GrandpaId)>,
    root_key: AccountId,
    endowed_accounts: Vec<AccountId>,
    _enable_println: bool,
) -> serde_json::Value {
    serde_json::json!({
        "balances": {
            // Configure pre-funded accounts (for gas fees)
            "balances": endowed_accounts
                .iter()
                .cloned()
                .map(|k| (k, 1_000_000_000_000_000u128))
                .collect::<Vec<_>>(),
        },
        "aura": {
            // Configure initial block production authorities
            "authorities": initial_authorities.iter().map(|x| (x.0.clone())).collect::<Vec<_>>(),
        },
        "grandpa": {
            // Configure initial finality authorities
            "authorities": initial_authorities
                .iter()
                .map(|x| (x.1.clone(), 1))
                .collect::<Vec<_>>(),
        },
        "sudo": {
            // Sudo key (remove in production or use governance-controlled account)
            "key": Some(root_key),
        },
        "council": {
            // Configure initial council members (journalism org representatives)
            // In production, this should match validator authorities
            "members": initial_authorities
                .iter()
                .enumerate()
                .filter(|(idx, _)| *idx < 10) // Max 10 initial council members
                .map(|(_, (aura_id, _))| {
                    // Convert AuraId to AccountId
                    // This is a placeholder - in production, use proper account derivation
                    get_account_id_from_seed::<sr25519::Public>("Alice")
                })
                .collect::<Vec<_>>(),
            "phantom": None,
        },
        "democracy": {},
        "treasury": {},
        "birthmark": {
            // Initialize birthmark pallet (currently no genesis config needed)
        },
    })
}
