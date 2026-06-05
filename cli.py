#!/usr/bin/env python3

import pathlib
import requests
import logging
import csv
import argparse
import json

file_path = pathlib.Path(__file__)
working_dir = file_path.parent

logger = logging.getLogger(file_path.stem)


elo_per_team = {}
alpha_3_to_2 = {}
alpha_3_to_name = {}


def main(args):
    iso_3166 = json.loads(
        pathlib.Path("/usr/share/iso-codes/json/iso_3166-1.json").read_text()
    )
    for item in iso_3166["3166-1"]:
        alpha_3_to_2[item["alpha_3"]] = item["alpha_2"]
        alpha_3_to_name[item["alpha_3"]] = item["name"]
    alpha_3_to_2["SCT"] = "SQ"
    alpha_3_to_name["SCT"] = "Scotland"
    logger.info(f"{working_dir = }")
    elo_tsv = working_dir.joinpath("2026_World_Cup.tsv")
    if not elo_tsv.is_file():
        logger.info(f"Downloading Elo ratings file: {elo_tsv}")
        with requests.get("https://www.eloratings.net/2026_World_Cup.tsv") as r:
            r.raise_for_status()
            elo_tsv.write_bytes(r.content)
    with elo_tsv.open() as f:
        reader = csv.reader(f, dialect="excel-tab")
        for row in reader:
            elo_per_team[row[2]] = int(row[3])

    highest_elo = max(elo_per_team.values())
    logger.info(f"Highest Elo rating: {highest_elo}")
    lowest_elo = min(elo_per_team.values())
    logger.info(f"Lowest Elo rating: {lowest_elo}")
    max_diff = highest_elo - lowest_elo
    logger.info(f"Max Elo rating difference: {max_diff}")
    avg_goals = 2.69

    def calculate_win_probability(country1, country2):
        diff1 = elo_per_team[alpha_3_to_2[country1]] - lowest_elo
        diff2 = elo_per_team[alpha_3_to_2[country2]] - lowest_elo
        cupwinratio1 = diff1 / max_diff
        cupwinratio2 = diff2 / max_diff
        goals1 = round(cupwinratio1 / (cupwinratio1 + cupwinratio2) * avg_goals)
        goals2 = round(cupwinratio2 / (cupwinratio1 + cupwinratio2) * avg_goals)
        country1 = alpha_3_to_name[country1]
        country2 = alpha_3_to_name[country2]
        return {
            "country1": country1,
            "country2": country2,
            "goals1": goals1,
            "goals2": goals2,
            "matchwinratio1": cupwinratio1 / (cupwinratio1 + cupwinratio2),
            "matchwinratio2": cupwinratio2 / (cupwinratio1 + cupwinratio2),
            "winner": get_winner(goals1, goals2, country1, country2),
        }

    def get_winner(goals1, goals2, country1, country2):
        if goals1 == goals2:
            return "tie"
        elif goals1 < goals2:
            return country2
        else:
            return country1

    print(calculate_win_probability(args.country1.upper(), args.country2.upper()))


if __name__ == "__main__":
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("country1", type=str, help="First country")
    parser.add_argument("country2", type=str, help="Second country")
    args = parser.parse_args()
    main(args)
