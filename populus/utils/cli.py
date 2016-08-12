import itertools
import click

from .transactions import (
    is_account_locked,
    get_contract_address_from_txn,
)


def select_chain(project):
    chain_options = set(project.config.chains.keys())

    choose_chain_msg = "\n".join(itertools.chain((
        "Available Chains",
        "----------------",
    ), (
        "{0} - {1}".format(chain_index, chain_name)
        for chain_index, chain_name in enumerate(sorted(chain_options))
    ), (
        "",
        "Enter ether the name, or number of the desired chain"
    )))
    chain_name = click.prompt(choose_chain_msg)
    if chain_name in chain_options:
        return chain_name
    elif chain_name.isdigit() and int(chain_name) < len(chain_options):
        return sorted(chain_options)[int(chain_name)]
    else:
        raise click.Abort(
            "Invalid choice: {0}.  Please choose from one of the "
            "provided options.".format(chain_name)
        )


def select_account(chain):
    all_accounts = chain.web3.eth.accounts
    if not all_accounts:
        raise click.Abort("No accounts found on chain.")
    unlocked_accounts = {
        account for account in all_accounts
        if not is_account_locked(chain.web3, account)
    }

    pick_account_message = '\n'.join(itertools.chain((
        "Accounts",
        "-----------------",
    ), (
        "{index} - {account}{extra}".format(
            account=account,
            extra=" (unlocked)" if account in unlocked_accounts else "",
            index=index,
        ) for (index, account) in enumerate(all_accounts)
    ), (
        "",
        "Enter the account address or the number of the desired account",
    )))

    account_choice = click.prompt(
        pick_account_message,
        default=chain.web3.eth.defaultAccount,
    )

    if account_choice in set(all_accounts):
        return account_choice
    elif account_choice.isdigit() and int(account_choice) < len(all_accounts):
        return all_accounts[int(account_choice)]
    else:
        raise click.Abort(
            "Invalid choice: {0}.  Please choose from one of the "
            "provided options.".format(account_choice)
        )


def request_account_unlock(chain, account, timeout):
    if not is_account_locked(chain.web3, account):
        raise click.Abort(
            "The account `{0}` is already unlocked".format(account)
        )

    unlock_account_msg = (
        "Please provide the password to unlock account `{0}`."
    )
    unlock_successful = chain.web3.personal.unlockAccount(
        account,
        click.prompt(unlock_account_msg, hide_input=True),
        timeout,
    )
    if not unlock_successful:
        raise click.Abort("Unable to unlock account: `{0}`".format(account))


def deploy_contract_and_verify(ContractFactory, contract_name):
    web3 = ContractFactory.web3

    if is_account_locked(web3, web3.eth.defaultAccount):
        raise click.Abort("The default `from` address must be unlocked.")

    click.echo("Deploying {0}".format(contract_name))

    deploy_txn_hash = ContractFactory.deploy()
    deploy_txn = web3.eth.getTransaction(deploy_txn_hash)

    click.echo("Deploy Transaction Sent: {0}".format(deploy_txn_hash))
    click.echo("Waiting for confirmation...")

    contract_address = get_contract_address_from_txn(
        web3=web3,
        txn_hash=deploy_txn_hash,
        timeout=180,
    )
    deploy_receipt = web3.eth.getTransactionReceipt(deploy_txn_hash)

    click.echo((
        "\n"
        "Transaction Mined\n"
        "=================\n"
        "Tx Hash      : {0}\n"
        "Address      : {1}\n"
        "Gas Provided : {2}\n"
        "Gas Used     : {3}\n\n".format(
            deploy_txn_hash,
            contract_address,
            deploy_txn['gas'],
            deploy_receipt['gasUsed'],
        )
    ))

    # Verification
    deployed_code = web3.eth.getCode(contract_address)

    if ContractFactory.code_runtime:
        click.echo("Verifying deployed bytecode...")
        is_bytecode_match = deployed_code != ContractFactory.code_runtime
        if is_bytecode_match:
            click.echo(
                "Verified contract bytecode @ {0} matches expected runtime "
                "bytecode".format(contract_address)
            )
        else:
            raise click.Abort(
                "Bytecode @ {0} does not match expected contract bytecode.\n\n"
                "expected : '{1}'\n"
                "actual   : '{2}'\n".format(
                    contract_address,
                    ContractFactory.code_runtime,
                    deployed_code,
                )
            )
    else:
        click.echo(
            "No runtime available.  Falling back to verifying non-empty "
            "bytecode."
        )
        if len(deployed_code) <= 2:
            raise click.Abort(
                "Bytecode @ {0} is unexpectedly empty.".format(contract_address)
            )
        else:
            click.echo(
                "Verified bytecode @ {0} is non-empty".format(contract_address)
            )
    return ContractFactory(address=contract_address)
