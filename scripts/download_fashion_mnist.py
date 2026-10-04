import gzip
import hashlib
import shutil
import urllib.request

# Official Fashion-MNIST files
BASE_URL = "https://raw.githubusercontent.com/zalandoresearch/fashion-mnist/master/data/fashion/"

FILES = {
    "train-images-idx3-ubyte.gz": "8d4fb7e6c68d591d4c3dfef9ec88bf0d",
    "train-labels-idx1-ubyte.gz": "25c81989df183df01b3e8a0aad5dffbe",
    "t10k-images-idx3-ubyte.gz": "bef4ecab320f06d8554ea6380940ec79",
    "t10k-labels-idx1-ubyte.gz": "bb300cfdad3c16e7a12a480ee83cd310",
}

from research_cli import ROOT, arguments, protect_evidence, run

OUTPUT_DIR = ROOT / "data/raw/fashion_mnist"


def calculate_md5(file_path):
    md5 = hashlib.md5()

    with open(file_path, "rb") as file:
        while chunk := file.read(1024 * 1024):
            md5.update(chunk)

    return md5.hexdigest()


def download_file(filename, expected_md5):
    destination = OUTPUT_DIR / filename

    if destination.exists():
        if calculate_md5(destination) == expected_md5:
            print(f"Already downloaded and verified: {filename}")
            return destination

        raise RuntimeError(f"Existing file failed checksum; preserve it for review: {destination}")

    print(f"Downloading: {filename}")
    urllib.request.urlretrieve(BASE_URL + filename, destination)

    actual_md5 = calculate_md5(destination)

    if actual_md5 != expected_md5:
        raise RuntimeError(
            f"Checksum failed for {filename}\nExpected: {expected_md5}\nReceived: {actual_md5}"
        )

    print(f"Verified: {filename}")
    return destination


def extract_file(compressed_path):
    extracted_path = compressed_path.with_suffix("")

    if extracted_path.exists():
        print(f"Already extracted: {extracted_path.name}")
        return

    print(f"Extracting: {compressed_path.name}")

    with gzip.open(compressed_path, "rb") as source:
        with open(extracted_path, "wb") as destination:
            shutil.copyfileobj(source, destination)

    print(f"Extracted: {extracted_path.name}")


def main():
    global OUTPUT_DIR
    args = arguments("download_fashion_mnist")
    OUTPUT_DIR = args.output
    protect_evidence(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Saving Fashion-MNIST to: {OUTPUT_DIR.resolve()}\n")

    for filename, expected_md5 in FILES.items():
        compressed_path = download_file(filename, expected_md5)
        extract_file(compressed_path)

    print("\nFashion-MNIST downloaded successfully.")
    print(f"Dataset location: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    run(main)
