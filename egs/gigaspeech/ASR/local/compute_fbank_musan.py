#!/usr/bin/env python3
# Copyright    2021  Johns Hopkins University (Piotr Żelasko)
# Copyright    2021  Xiaomi Corp.             (Fangjun Kuang)
#
# See ../../../../LICENSE for clarification regarding multiple authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from pathlib import Path

import torch
from lhotse import (
    CutSet,
    KaldifeatFbank,
    KaldifeatFbankConfig,
    combine,
)
from lhotse.recipes.utils import read_manifests_if_cached

# Torch's multithreaded behavior needs to be disabled or
# it wastes a lot of CPU and slow things down.
# Do this outside of main() in case it needs to take effect
# even when we are not invoking the main (e.g. when spawning subprocesses).
torch.set_num_threads(1)
torch.set_num_interop_threads(1)


def compute_fbank_musan():
    src_dir = Path("data/manifests")
    output_dir = Path("data/fbank")

    # number of workers in dataloader
    num_workers = 10

    # number of seconds in a batch
    batch_duration = 600

    dataset_parts = (
        "music",
        "speech",
        "noise",
    )

    manifests = read_manifests_if_cached(
        prefix="musan", dataset_parts=dataset_parts, output_dir=src_dir
    )
    assert manifests is not None

    musan_cuts_path = output_dir / "cuts_musan.json.gz"

    if musan_cuts_path.is_file():
        logging.info(f"{musan_cuts_path} already exists - skipping")
        return

    logging.info("Extracting features for Musan")

    device = torch.device("cpu")
    if torch.cuda.is_available():
        device = torch.device("cuda", 0)
    extractor = KaldifeatFbank(KaldifeatFbankConfig(device=device))

    logging.info(f"device: {device}")

    musan_cuts = (
        CutSet.from_manifests(
            recordings=combine(
                part["recordings"] for part in manifests.values()
            )
        )
        .cut_into_windows(10.0)
        .filter(lambda c: c.duration > 5)
        .compute_and_store_features_batch(
            extractor=extractor,
            storage_path=f"{output_dir}/feats_musan",
            num_workers=num_workers,
            batch_duration=batch_duration,
        )
    )
    musan_cuts.to_json(musan_cuts_path)


def main():
    formatter = (
        "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
    )
    logging.basicConfig(format=formatter, level=logging.INFO)

    compute_fbank_musan()


if __name__ == "__main__":
    main()
