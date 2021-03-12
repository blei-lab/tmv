from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
import os
import psutil

class Command(BaseCommand):
    def handle(self, *args, **options):

        pid = os.getpid()

        for p in psutil.process_iter():
            if "refresh_apis" in p.cmdline() and p.pid != pid:
                print("api getting is already running... skipping for today")
                return

        print("\n\n#########\n\n")
        print("searching for tweets from the api")
        call_command('api_searches')
        print("\n\n#########\n\n")
        print("collecting users and their tweets from the api")
        call_command('hydrate_users')
        #print("hydrating empty tweets with the api")
        #call_command('hydrate_tweets')
