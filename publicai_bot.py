import asyncio
import json
import os
import time
from datetime import datetime
import pytz
import hashlib
import random
import string
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from colorama import Fore, Style
from dotenv import load_dotenv
import traceback # <-- Added this line

# Load environment variables from .env file
load_dotenv()

class PublicAIBot:
    def __init__(self):
        self.BASE_URL = "https://publicai.io/api/data_hunter/ping"
        self.HEADERS_TEMPLATE = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Content-Type": "application/json",
            "Origin": "chrome-extension://icbbdbflabjciapbohkkmfjaangfjagf",
            "User-Agent": FakeUserAgent().random,
            "Connection": "keep-alive"
        }
        self.PROXY_LIST = self.load_proxies()
        self.proxy_index = 0

        # Set timezone for logging (from previous context, Asia/Jakarta)
        self.wib = pytz.timezone('Asia/Jakarta')

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(self.wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{message}"
        )

    def load_proxies(self):
        if os.path.exists("proxies.txt"):
            with open("proxies.txt", "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
            self.log(f"{Fore.GREEN}Loaded {len(proxies)} proxies from proxies.txt.{Style.RESET_ALL}")
            return proxies
        return []

    def get_proxy(self, rotate_proxy=True):
        if not self.PROXY_LIST:
            return None, None

        if rotate_proxy:
            proxy = self.PROXY_LIST[self.proxy_index]
            self.proxy_index = (self.proxy_index + 1) % len(self.PROXY_LIST)
        else:
            proxy = self.PROXY_LIST[self.proxy_index] # Use current proxy without rotation

        connector = ProxyConnector.from_url(proxy)
        return connector, proxy

    def generate_random_string(self, length=4):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def calculate_signature(self, t_val, n_val):
        # Parameters for hash (sorted alphabetically by key)
        # The payload is an empty JSON object, so it does not contribute to the hash string directly.
        params_for_hash = {
            'n': str(n_val),
            't': str(t_val)
        }

        sorted_keys = sorted(params_for_hash.keys())
        hash_string_parts = []
        for key in sorted_keys:
            hash_string_parts.append(f"{key}{params_for_hash[key]}")

        hash_input_string = "".join(hash_string_parts)
        md5_hash = hashlib.md5(hash_input_string.encode('utf-8')).hexdigest()
        return md5_hash

    async def send_ping(self, account_email, access_token, use_proxy, rotate_proxy):
        connector = None
        proxy_info = "No Proxy"
        if use_proxy:
            connector, proxy_info = self.get_proxy(rotate_proxy)

        headers = self.HEADERS_TEMPLATE.copy()
        headers["Authorization"] = f"Bearer {access_token}"

        # Generate timestamp and random string for current request
        t_val = int(time.time() * 1000) # Current Unix timestamp in milliseconds
        n_val = self.generate_random_string() # New random 4-char string

        # Calculate the signature based on t and n
        s_val = self.calculate_signature(t_val, n_val)

        # Query parameters for the URL
        params = {
            't': t_val,
            'n': n_val,
            's': s_val
        }

        # The payload is an empty JSON object, as observed in the network capture
        payload = {}

        try:
            timeout = ClientTimeout(total=30) # 30 second timeout
            async with ClientSession(connector=connector, headers=headers, timeout=timeout) as session:
                self.log(f"{Fore.MAGENTA}[ Account: {Style.RESET_ALL}{Fore.WHITE}{account_email}{Style.RESET_ALL}{Fore.MAGENTA} | Proxy: {Style.RESET_ALL}{Fore.WHITE}{proxy_info}{Style.RESET_ALL}{Fore.MAGENTA} ] {Fore.YELLOW}Sending PublicAI ping...{Style.RESET_ALL}")

                async with session.post(self.BASE_URL, json=payload, params=params) as response:
                    response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

                    data = await response.json()

                    if response.status == 200:
                        self.log(
                            f"{Fore.MAGENTA}[ Account: {Style.RESET_ALL}{Fore.WHITE}{account_email}{Style.RESET_ALL}"
                            f"{Fore.MAGENTA} | Status:{Style.RESET_ALL}{Fore.GREEN} SUCCESS {Style.RESET_ALL}"
                            f"{Fore.MAGENTA} ] {Fore.WHITE}Ping successful: {data.get('msg', 'No message')}{Style.RESET_ALL}"
                        )
                    else:
                        self.log(
                            f"{Fore.MAGENTA}[ Account: {Style.RESET_ALL}{Fore.WHITE}{account_email}{Style.RESET_ALL}"
                            f"{Fore.MAGENTA} | Status:{Style.RESET_ALL}{Fore.RED} FAILED {Style.RESET_ALL}"
                            f"{Fore.MAGENTA} ] {Fore.RED}Ping failed with status {response.status}: {data.get('msg', 'No message')}{Style.RESET_ALL}"
                        )
        except Exception as e:
            self.log(
                f"{Fore.MAGENTA}[ Account: {Style.RESET_ALL}{Fore.WHITE}{account_email}{Style.RESET_ALL}"
                f"{Fore.MAGENTA} | Proxy: {Style.RESET_ALL}{Fore.WHITE}{proxy_info}{Style.RESET_ALL}"
                f"{Fore.MAGENTA} ] {Fore.RED}Error sending ping: {Style.RESET_ALL}"
            )
            # Print the full traceback for detailed debugging
            traceback.print_exc() # <-- Added this line for full error details
            self.log(f"{Fore.MAGENTA}[ Account: {Style.RESET_ALL}{Fore.WHITE}{account_email}{Style.RESET_ALL} ] {Fore.CYAN}Waiting for 1 hour until next ping...{Style.RESET_ALL}")


    async def run_account(self, account_email, access_token, use_proxy, rotate_proxy):
        while True:
            await self.send_ping(account_email, access_token, use_proxy, rotate_proxy)
            self.log(f"{Fore.MAGENTA}[ Account: {Style.RESET_ALL}{Fore.WHITE}{account_email}{Style.RESET_ALL}{Fore.MAGENTA} ] {Fore.CYAN}Waiting for 1 hour until next ping...{Style.RESET_ALL}")
            await asyncio.sleep(3600) # Wait for 1 hour (3600 seconds)

    async def main(self):
        self.clear_terminal()
        self.log(f"{Fore.CYAN + Style.BRIGHT}[ PublicAI - BOT Started ]{Style.RESET_ALL}")

        # --- CONFIGURE YOUR ACCOUNTS HERE ---
        # Each tuple should be: (email, bearer_token, use_proxy_for_this_account, rotate_proxy_for_this_account)
        # Your Bearer token will be loaded from the .env file.
        # Make sure 'proxies.txt' exists in the same directory if you set use_proxy to True.
        accounts_to_run = [
            ("susdre35@gmail.com", os.getenv("PUBLICAI_BEARER_TOKEN"), False, False),
            # Example with proxy:
            # ("your_email_account2@example.com", os.getenv("ANOTHER_PUBLICAI_TOKEN"), True, True),
            # You can add as many accounts as you need.
        ]
        # -----------------------------------

        tasks = []
        for email, token, use_proxy, rotate_proxy in accounts_to_run:
            if not token:
                self.log(f"{Fore.RED}Skipping account {email}: No bearer token found in .env. Ensure PUBLICAI_BEARER_TOKEN is set.{Style.RESET_ALL}")
                continue
            tasks.append(asyncio.create_task(self.run_account(email, token, use_proxy, rotate_proxy)))

        if not tasks:
            self.log(f"{Fore.RED}No accounts configured or valid tokens found. Please update 'accounts_to_run'.{Style.RESET_ALL}")
            return

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.log(f"{Fore.RED+Style.BRIGHT}[ EXIT ] PublicAI - BOT stopped by user.{Style.RESET_ALL}")
        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}An unexpected error occurred: {e}{Style.RESET_ALL}")
            traceback.print_exc() # Also print traceback for unexpected main errors

if __name__ == "__main__":
    bot = PublicAIBot()
    asyncio.run(bot.main())
