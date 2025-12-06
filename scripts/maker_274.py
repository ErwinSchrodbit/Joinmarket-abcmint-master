import os
import sys
import importlib.util


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    here = os.path.dirname(__file__)
    
    # Add joinmarket-clientserver-master/src to sys.path
    jm_root = os.path.join(here, '..', 'joinmarket-clientserver-master', 'src')
    if jm_root not in sys.path:
        sys.path.insert(0, os.path.abspath(jm_root))
        
    abcmint_iface_path = os.path.join(here, '..', 'src', 'jmclient', 'abcmint_interface.py')
    jsonrpc_path = os.path.join(jm_root, 'jmclient', 'jsonrpc.py')

    abcmint_iface = _load_module(abcmint_iface_path, 'abcmint_interface')
    jm_jsonrpc = _load_module(jsonrpc_path, 'jm_jsonrpc')

    host = os.environ.get('ABCMINT_RPC_HOST', '127.0.0.1')
    port = int(os.environ.get('ABCMINT_RPC_PORT', '8332'))
    user = os.environ.get('ABCMINT_RPC_USER', '')
    password = os.environ.get('ABCMINT_RPC_PASSWORD', '')

    if not all([host, port, user, password]):
        print('Missing RPC environment variables', file=sys.stderr)
        sys.exit(1)

    rpc = jm_jsonrpc.JsonRpc(host, port, user, password)
    iface = abcmint_iface.ABCmintBlockchainInterface(rpc, '')

    addr = iface.get_new_address()
    print(addr)


if __name__ == '__main__':
    main()