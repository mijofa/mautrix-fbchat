#!/usr/bin/python3
import argparse
import getpass
import os.path
import secrets
import socket
import sys

import yaml

import fbchat


argparser = argparse.ArgumentParser(
    description="Log in to Facebook chat and create a registration yaml config file for Synapse and mautrix-fbchat to use")
argparser.add_argument(
    'yaml_filename',
    nargs="?",
    help=("Filename to save the yaml config to."
          "If file already exists, just refresh the Facebook session cookies"))
argparser.add_argument(
    '-m', '--matrix-user',
    required=True,
    help="Username of the local Matrix user to bridge with Facebook (localpart only)")
argparser.add_argument(
    '-f', '--fb-user',
    required=True,
    help="Facebook email address, username, or phone number to log in with")
argparser.add_argument(
    '-p', '--port',
    default=8091, type=int,
    help="Port number to configure the app service listener to run on")
argparser.add_argument(
    '-b', '--baseurl',
    default='http://127.0.0.1:8008',
    help="Matrix server base URL")
argparser.add_argument(
    '-d', '--domain',
    default=socket.getfqdn(),
    help='The domain of the matrix server')
args = argparser.parse_args()


if args.yaml_filename and os.path.isfile(args.yaml_filename):
    with open(args.yaml_filename, 'r') as f:
        registration_data = yaml.load(f)

    if args.fb_user and args.fb_user != registration_data['fbchat_username']:
        raise Exception("Requested Facebook username doesn't match config")
    elif not args.fb_user:
        args.fb_user = registration_data['fbchat_username']
    fb_session = registration_data['fbchat_session']
else:
    registration_data = None

    print("If prompted for 2FA code, you can give an empty code after approving the login from a logged in session")
    fb_session = {}

args.fb_user = input("Facebook username, email address, or phone number: ") if not args.fb_user else args.fb_user


try:
    fb = fbchat.Client(
        email=args.fb_user,
        password='?',  # Try using the session cookies before actually asking the user for a password
        session_cookies=fb_session,
        max_tries=1,
    )
except fbchat._exception.FBchatUserError as e:
    if e.args[0].startswith('Login failed. Check email/password'):
        fb = fbchat.Client(
            email=args.fb_user,
            password=getpass.getpass("Facebook password (will not echo): "),
            session_cookies=fb_session,
        )
    else:
        raise

if registration_data:
    if registration_data['fbchat_uid'] != fb.uid:
        raise fbchat._exception.FBchatUserError("Logged in Facebook account doesn't match config")
    hs_token = registration_data['hs_token']
    as_token = registration_data['as_token']
else:
    hs_token = secrets.token_hex(),  # Does this follow the same spec as Matrix expects?
    as_token = secrets.token_hex(),  # Perhaps it could be more random?

registration_data = {
    'id': f"mautrix-fbchat_{fb.uid}",
    'url': f"http://127.0.0.1:{args.port}",
    'hs_token': hs_token,
    'as_token': as_token,
    'namespaces': {
        # Yes these are single-item lists, it's not a typo, Synapse actually needs it to work that way.
        'users': [
            {'exclusive': True, 'regex': f"@fbchat_{fb.uid}_.*"}
            {'exclusive': False, 'regex': f"@{args.matrix_user}:{args.domain}"}  # FIXME: Is this incredibly evil?
        ],
        'aliases': [
            {'exclusive': True, 'regex': f"#fbchat_{fb.uid}_.*"}
        ],
        'rooms': []  # FIXME: Can I get away with just removing this?
    },
    'sender_localpart': f"fbchat_{fb.uid}",
    'rate_limited': True,
    'protocols': ["fbchat"],

    # I would like to avoid having multiple config files sharing some of the same secret tokens.
    # So instead of copying the as/hs token values into another config file along with the Facebook auth tokens,
    # I'm just going include the Facebook auth tokens in with the Synapse config and rely on Synapse ignoring it.
    #
    # FIXME: Can I store this info in Matrix somehow?
    'fbchat_username': fb.email,  # fbchat library won't let me login with *just* the session cookies, so use the username too.
    'fbchat_uid': fb.uid,  # Just so we can later confirm who this config
    'fbchat_session': fb.getSession(),  # FIXME: Do I need all the session cookies? Is this yaml file stored securely?

    'matrix_domain': args.domain,
    'matrix_baseurl': args.baseurl,
    'matrix_user_localpart': args.matrix_user,
}

yaml_filename = args.yaml_filename if args.yaml_filename else f"fbchat_{fb.uid}_appservice.yaml"
with open(yaml_filename, 'w') as f:
    yaml.dump(registration_data, f)
    output_filename = f.name

## Actually logging out invalidates the session cookies.
## FIXME: Session cookies are being a pain in the arse and hardly working anyway, how well do app passwords work?
## FIXME: App passwords don't work at all... what the fuck?
# fb.logout()  # Probably happens automatically with garbage collection, but can't hurt

print(f"\n\nCopy {f.name} into a more sensible place and add to Synapse's app_service_config_files option\n")
