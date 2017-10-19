#!/usr/bin/env python
#
# The code that powers /u/makegist Reddit bot
#
# GITHUB Repository for Makegist Reddit Bot : https://github.com/hexagonist/MakegistRedditBot
# Author : hexagonist (https://github.com/hexagonist)
"""MIT License
Copyright 2017 Hexagonist

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import sys

if sys.version_info[0] >= 3:
    from urllib.request import urlopen
else:
    from urllib import urlopen

import json
import praw
import credentials
from praw.models import Comment
import re

import time

DEFAULT_FILENAME = "filename"
BOT_VERSION = "0.1.0"
CONTACT_USERNAME = "offdutyhuman"

def main():
    # This code runs every x minutes with cron
    # so we don't need to run it as a loop
    reddit = praw.Reddit(**credentials.reddit)
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

def upload_gist(data):
    """
        Attempt to create a new github gist with the supplied data
    """
    print('Uploading gist')
    url = 'https://api.github.com/gists'
    response = urlopen(url, data=data)
    code = response.getcode()

    if code != 201:
        raise ValueError("Invalid response", response.read())

    return json.loads(response.read())

def make_gist(files, description="", public=True):
    """
        Make a gist from the supplied arguments
    """
    data = json.dumps(files).encode('utf-8')
    data = upload_gist(data)

    # Id represents the id of the gist
    # and files represents the meta-data for the files in this gist
    return (data['id'], data['files'])

def is_valid_mention(mention):
    """
        Check that the submission follows these:
            - not an old mention
            - can't be a root comment since it would mean no parent comment
            - check that the formatting is correct
                aka they're not just mentioning in a random comment
    """
    return (isinstance(mention, Comment)
        and mention.new
        and not mention.is_root
        and re.search(r"^(?:\+/u/makegist)", mention.body))

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
        "Here is your gist : [https://gist.github.com/{}](https://gist.github.com/{})".format(gist_id,gist_id),
        "----",
        "To clone the gist repo :",
        "    git clone https://gist.github.com/{}.git out_folder".format(gist_id),
        "----",
        "To download the file directly :",
        "    curl -L {} > {}".format(raw_url, filename),
        "----",
        "|".join([
            "^(v.{})".format(BOT_VERSION),
            "^(To summon me : **+/u/makegist filename.ext**)",
            "[^Contact](http://www.reddit.com/r/{})".format(CONTACT_USERNAME)])])

def check_mentions(reddit):
    """
        Check the reddit inbox for mentions and process them as necessary
    """
    valid_mentions = [mention for mention in reddit.inbox.mentions() if is_valid_mention(mention)]

    for valid_mention in valid_mentions:
        comment = valid_mention.parent()

        # parse the comment arguments
        filename = get_mention_args(valid_mention.body)
        codeblock = parse_code(comment.body)

        # make sure we were able to retrieve code in the comment
        if codeblock:
            # create gist and reply with gist link
            files = {
                "files" : {
                    filename : {
                        "content" : codeblock
                    }
                }
            }
            try:
                gist_id, files = make_gist(files)
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
