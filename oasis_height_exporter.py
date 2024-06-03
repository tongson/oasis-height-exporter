from urllib.parse import urlparse
import time
import argparse
import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import prometheus_client
from prometheus_client import REGISTRY


def read_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporter of external Oasis block height."
    )
    parser.add_argument(
        "--port",
        metavar="PORT",
        type=int,
        default=9099,
        help="The port used to export the metrics. Default is 9099.",
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        default=False,
        type=str,
        help="URL of Oasis API endpoint.",
    )
    parser.add_argument(
        "--freq",
        metavar="SEC",
        type=int,
        default=300,
        help="Update frequency in seconds. Default is 300 seconds (5 minutes).",
    )
    return parser.parse_args()


def get_height(url: str) -> float:
    retry_strategy = Retry(
        total=4,
        status_forcelist=[104, 408, 425, 429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    try:
        resp = session.get(url)
    except Exception as e:
        return float(0)
    else:
        if resp.status_code == 200:
            data = resp.json()
            height = data["data"]["list"][0]["height"]
            return float(height)
        else:
            return float(0)


if __name__ == "__main__":
    args = read_args()
    for coll in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(coll)
    try:
        prometheus_client.start_http_server(args.port)
    except Exception as e:
        e.add_note("\nError starting HTTP server.")
        raise
    else:
        register = prometheus_client.Gauge(
            "oasis_latest_block_height",
            "Oasis Latest Block Height",
            ["external_endpoint"],
        )
        while True:
            height = get_height(args.url)
            sys.stdout.write(str(height) + "\n")
            if height > 1:
                register.labels(urlparse(args.url).hostname).set(height)
            time.sleep(args.freq)
