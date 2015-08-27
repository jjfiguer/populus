import pytest

from eth_rpc_client import Client

from populus.contracts import (
    deploy_contract,
    get_contract_address_from_txn,
)

from ethereum.abi import ContractTranslator
from ethereum import utils as ethereum_utils


@pytest.fixture
def deployed_math(Math, rpc_server, rpc_client, eth_coinbase):
    deploy_txn_hash = deploy_contract(
        rpc_client,
        Math,
        _from=eth_coinbase,
    )
    contract_addr = get_contract_address_from_txn(rpc_client, deploy_txn_hash)
    assert contract_addr
    math = Math(contract_addr, rpc_client)
    return math


def test_contract_return13_function_signature(deployed_math):
    assert deployed_math.return13.abi_function_signature == 371289913
    assert deployed_math.return13.encoded_abi_function_signature == '\x16!o9'
    assert deployed_math.return13.get_call_data([]) == '16216f39'


def test_contract_add_function_signature(deployed_math):
    assert deployed_math.add.abi_function_signature == 2784215611
    assert deployed_math.add.encoded_abi_function_signature == '\xa5\xf3\xc2;'
    assert deployed_math.add.get_call_data((3, 4)) == 'a5f3c23b00000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000004'


def test_contract_multiply7_function_signature(deployed_math):
    assert deployed_math.multiply7.abi_function_signature == 3707058097
    assert deployed_math.multiply7.encoded_abi_function_signature == '\xdc\xf57\xb1'
    assert deployed_math.multiply7.get_call_data((3,)) == 'dcf537b10000000000000000000000000000000000000000000000000000000000000003'


def test_contract_function_call_return13(deployed_math, eth_coinbase):
    ret = deployed_math.return13.call(_from=eth_coinbase)
    assert ret == 13


def test_contract_function_call_multiply7(deployed_math, eth_coinbase):
    ret = deployed_math.multiply7.call(3, _from=eth_coinbase)
    assert ret == 21


def test_contract_function_call_add(deployed_math, eth_coinbase):
    ret = deployed_math.add.call(25, 35, _from=eth_coinbase)
    assert ret == 60


def test_sent_transaction_with_value(deployed_math, eth_coinbase, rpc_client):
    assert deployed_math.get_balance() == 0
    txn_hash = deployed_math.add.sendTransaction(35, 45, _from=eth_coinbase, value=1000)
    txn_receipt = rpc_client.get_transaction_receipt(txn_hash)
    assert deployed_math.get_balance() == 1000
