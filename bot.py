#!/usr/bin/env python
#
# The code that powers /u/makegist Reddit bot
#
# GITHUB Repository for Makegist Reddit Bot : https://github.com/hexagonist/MakegistRedditBot
# Author : hexagonist (https://github.com/hexagonist)
# License : MIT License
#

import sys

# if sys.version_info[0] >= 3:
#     from urllib.request import urlopen
# else:
#     from urllib import urlopen

import urllib2

import json
import praw
import credentials
from praw.models import Comment
import re

import time

DEFAULT_FILENAME = "filename"
BOT_VERSION = "0.1.3"
CONTACT_USERNAME = "OffDutyHuman"

def main():
    # This code runs every x minutes with cron
    # so we don't need to run it as a loop
    reddit = praw.Reddit(**credentials.reddit)
    print "Checking mentions"
    check_mentions(reddit)

def run_as_loop(reddit):
    """
        Run the bot indefinitly
    """
    while True:
        print "Checking mentions"
        check_mentions(reddit)
        print "Sleeping for 60 seconds"
        time.sleep(60)

def parse_code(body):
    """
        Parse the code from the body
    """
    # Regex to match code block reddit comment
    regex = ur"^((?:(?:(?:[ ]{4}).*|)(?:[\r\n]+|$))+)"
    matches = re.findall(regex, body, re.MULTILINE)
    # remove all empty lines
    matches = [match for match in matches if match != "\n"]

    # remove leading 4 spaces used to create code blocks in reddit comments
    return re.sub(r"^    ", "", matches[0].strip('\r\n'), flags=re.M) if matches else ""

def upload_gist(data, auth_token):
    """
        Attempt to create a new github gist with the supplied data
    """
    print('Uploading gist')
    url = 'https://api.github.com/gists'
    req = urllib2.Request(url)
    req.add_header('Authorization', "token {}".format(auth_token))

    response = urllib2.urlopen(req, data=data)
    code = response.getcode()

    if code != 201:
        raise ValueError("Invalid response", response.read())

    return json.loads(response.read())

def make_gist(files, auth_token, description=""):
    """
        Make a gist from the supplied arguments
    """
    data = json.dumps(files).encode('utf-8')
    data = upload_gist(data, auth_token)

    # Id represents the id of the gist
    # and files represents the meta-data for the files in this gist
    return (data['id'], data['files'])

def is_valid_mention(mention):
    """
        Check that the submission follows these:
            - not an old mention
            - check that the formatting is correct
                aka they're not just mentioning in a random comment
    """
    return (isinstance(mention, Comment)
        and mention.new
        and "+/u/makegist" in mention.body)

def is_valid_filename(name):
    """
        Check that the filename is valid:
            - Does not start with a dot
            - Only contains alpha-numeric characters,
                dashes, underscores or dots
    """
    return bool(re.findall(ur"^(?!\.)[A-Za-z0-9\-_.]+", name))

def get_mention_args(body):
    """
        Retrieve and return the filename from the mention

        To summon the bot : "+/u/makegist <filename>"
    """
    regex = "^(?:\+/u/makegist)(?: ([A-Za-z\-_.]+))"
    matches = re.findall(regex, body, re.MULTILINE)
    return matches[0] if matches and is_valid_filename(matches[0]) else DEFAULT_FILENAME

def get_reply(gist_id, raw_url, filename):
    """
        Get the reply message for a mention
    """
    return "\n\n".join([
        "**&#x2757; Don't run code you don't understand**",
        "[Github Gist](https://gist.github.com/{})".format(gist_id),
        "----",
        "To clone the gist repo :",
        "    git clone https://gist.github.com/{}.git out_folder".format(gist_id),
        "----",
        "To download the file directly :",
        "    curl -L {} > {}".format(raw_url, filename),
        "----",
        "^( | )".join([
            "^(&#x1F916; v.{})".format(BOT_VERSION),
            "^(To summon me : **+/u^/makegist [filename.ext]**)",
            "[^(Source)](https://gist.github.com/hexagonist/33d4501f64d7a097d2b243fc67f0f489)",
            "[^(Contact)](http://www.reddit.com/r/{})".format(CONTACT_USERNAME)])])

def check_mentions(reddit):
    """
        Check the reddit inbox for mentions and process them as necessary
    """
    valid_mentions = [mention for mention in reddit.inbox.mentions() if is_valid_mention(mention)]

    for valid_mention in valid_mentions:
        # check if there is a codeblock in the current comment
        codeblock = parse_code(valid_mention.body)

        if not codeblock and not valid_mention.is_root:
            # if no code in comment and is not root comment -> check the parent
            codeblock = parse_code(valid_mention.parent().body)

        # parse the comment arguments
        filename = get_mention_args(valid_mention.body)

        # make sure we were able to retrieve code in the comment
        if codeblock:
            # create gist and reply with gist link
            files = {
                "files" : {
                    filename : {
                        "content" : codeblock
                    }
                },
                "public" : "true"
            }
            try:
                gist_id, files = make_gist(files, credentials.github_token)
            except ValueError as e:
                print e
                print "Error with : {}".format(valid_mention.id)
                continue # Something went wrong with the mention so skip comment

            valid_mention.reply(
                get_reply(
                    gist_id,
                    files[filename]['raw_url'],
                    filename))

    # mark all new mentions as read
    if valid_mentions:
        reddit.inbox.mark_read(valid_mentions)

if __name__ == '__main__':
    main()
