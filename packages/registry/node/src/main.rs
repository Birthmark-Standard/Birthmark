//! Birthmark Standalone Blockchain Node
//!
//! This is the main entry point for the Birthmark registry node, which provides
//! permanent, tamper-evident storage of image authentication records.

mod chain_spec;
mod cli;
mod command;
mod rpc;
mod service;

fn main() -> sc_cli::Result<()> {
    command::run()
}
