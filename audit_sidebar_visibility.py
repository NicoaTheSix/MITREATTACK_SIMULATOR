"""Compatibility entry point for the independent three-group sidebar audit. Flow: README.md."""
import argparse
from audit_sidebar_groups import main

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--loaded',action='store_true')
    parser.add_argument('--native-hidden',action='store_true')
    args=parser.parse_args()
    main(args.loaded,args.native_hidden)
