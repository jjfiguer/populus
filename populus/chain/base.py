from __future__ import absolute_import

import warnings

from pylru import lrucache

from eth_utils import (
    to_ordered_dict,
)

from populus.config.backend import (
    ContractBackendConfig,
)

from populus.contracts.provider import (
    Provider,
)
from populus.contracts.registrar import (
    Registrar,
)
from populus.contracts.store import (
    Store,
)

from populus.utils.config import (
    sort_prioritized_configs,
)
from populus.utils.contracts import (
    construct_contract_factories,
)
from populus.utils.functional import (
    cached_property,
)
from populus.utils.module_loading import (
    import_string,
)
from populus.utils.wait import (
    Wait,
)


class BaseChain(object):
    """
    Base class for how populus interacts with the blockchain.

    :param project: Instance of :class:`populus.project.Project`
    """
    project = None
    chain_name = None
    config = None
    _factory_cache = None

    def __init__(self, project, chain_name, chain_config):
        self.project = project
        self.chain_name = chain_name
        self.config = chain_config
        self._factory_cache = lrucache(128)
        self.initialize_chain()

    def initialize_chain(self):
        """
        Hook for initialization that is called during class instantiation.
        """
        pass

    #
    # Required Public API
    #
    def get_web3_config(self):
        web3_config = self.config.get_web3_config()
        return web3_config

    @property
    def web3_config(self):
        return self.get_web3_config()

    @cached_property
    def web3(self):
        if not self._running:
            raise ValueError("Chain must be running prior to accessing web3")
        return self.web3_config.get_web3()

    @property
    def wait(self):
        return Wait(self.web3)

    #
    # +--------------+
    # | Contract API |
    # +--------------+
    #
    @property
    @to_ordered_dict
    def contract_backend_configs(self):
        backend_configs = self.config.get_config('contracts.backends')
        sorted_backend_configs = sort_prioritized_configs(
            backend_configs,
            self.project.config
        )
        for backend_name, base_backend_config in sorted_backend_configs.items():
            yield backend_name, ContractBackendConfig(base_backend_config)

    @cached_property
    @to_ordered_dict
    def contract_backends(self):
        for backend_name, backend_config in self.contract_backend_configs.items():
            ProviderBackendClass = import_string(backend_config['class'])
            yield (
                backend_name,
                ProviderBackendClass(self, backend_config.get_config('settings')),
            )

    #
    # Provider
    #
    @property
    @to_ordered_dict
    def provider_backends(self):
        for backend_name, backend in self.contract_backends.items():
            if backend.is_provider:
                yield backend_name, backend

    @property
    def provider(self):
        if not self.provider_backends:
            raise ValueError(
                "Must have at least one provider backend "
                "configured\n{0}".format(self.contract_backend_configs)
            )
        return Provider(self, self.provider_backends)

    #
    # Registrar
    #
    @cached_property
    @to_ordered_dict
    def registrar_backends(self):
        for backend_name, backend in self.contract_backends.items():
            if backend.is_registrar:
                yield backend_name, backend

    @property
    def registrar(self):
        if not self.registrar_backends:
            raise ValueError(
                "Must have at least one registrar backend "
                "configured\n{0}".format(self.contract_backend_configs)
            )
        return Registrar(self, self.registrar_backends)

    #
    # Source
    #
    @property
    @to_ordered_dict
    def store_backends(self):
        for backend_name, backend in self.contract_backends.items():
            if backend.is_store:
                yield backend_name, backend

    @property
    def store(self):
        if not self.store_backends:
            raise ValueError(
                "Must have at least one store backend "
                "configured\n{0}".format(self.contract_backend_configs)
            )
        return Store(self, self.store_backends)

    #
    # Running the chain
    #
    _running = None

    def __enter__(self):
        self._running = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._running = False

    #
    # !!!! Deprecated !!!!
    #
    @cached_property
    def contract_factories(self):
        warnings.warn(DeprecationWarning(
            "The `contract_factories` property has been deprecated.  Please use "
            "the `chain.store` and `chain.provider` API to access contract "
            "factory data"
        ))
        compiled_contracts = self.project.compiled_contracts

        return construct_contract_factories(
            self.web3,
            compiled_contracts,
        )

    def get_contract_factory(self, contract_identifier):
        pass

    def is_contract_available(self, contract_identifier):
        pass

    def are_contract_factory_dependencies_available(self, contract_identifier):
        pass

    def get_contract(self, contract_identifier):
        pass

    def get_or_deploy_contract(self,
                               contract_identifier,
                               deploy_transaction=None,
                               deploy_args=None,
                               deploy_kwargs=None):
        """
        Same as get_contract but it will also lazily deploy the contract with
        the provided deployment arguments
        """
        pass

    def get_contract_address(self, contract_identifier):
        """
        Retrieve a contract address from the provider backends.
        """
        pass

    @property
    def deployed_contracts(self):
        pass
