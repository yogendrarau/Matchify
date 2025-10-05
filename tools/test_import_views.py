import importlib, sys, traceback

try:
    m = importlib.import_module('Matchifyapp.views')
    print('Imported Matchifyapp.views OK')
    print('has send_message:', hasattr(m, 'send_message'))
    print('has get_messages:', hasattr(m, 'get_messages'))
    # print a short list of attributes
    names = [a for a in dir(m) if not a.startswith('_')]
    print('attrs count:', len(names))
    print('sample attrs:', names[:40])
except Exception:
    traceback.print_exc()
    sys.exit(1)
