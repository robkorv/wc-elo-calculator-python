#!/usr/bin/env python3

import json
import pathlib
import requests
import logging
import csv
import argparse

file_path = pathlib.Path(__file__)
working_dir = file_path.parent

logger = logging.getLogger(file_path.stem)


elo_per_team = {}
fifa_code_to_alpha_2 = {}
fifa_code_to_name = {}


GROUPS = {
    "A": [
        ["MEX", "RSA"],
        ["KOR", "CZE"],
        ["CZE", "RSA"],
        ["MEX", "KOR"],
        ["RSA", "KOR"],
        ["CZE", "MEX"],
    ],
    "B": [
        ["CAN", "BOS"],
        ["QAT", "SUI"],
        ["SUI", "BOS"],
        ["CAN", "QAT"],
        ["SUI", "CAN"],
        ["BOS", "QAT"],
    ],
    "C": [
        ["BRA", "MAR"],
        ["HAI", "SCO"],
        ["SCO", "MAR"],
        ["BRA", "HAI"],
        ["MAR", "HAI"],
        ["SCO", "BRA"],
    ],
    "D": [
        ["USA", "PAR"],
        ["AUS", "TUR"],
        ["USA", "AUS"],
        ["TUR", "PAR"],
        ["PAR", "AUS"],
        ["TUR", "USA"],
    ],
    "E": [
        ["GER", "CUR"],
        ["CIV", "ECU"],
        ["GER", "CIV"],
        ["ECU", "CUR"],
        ["CUR", "CIV"],
        ["ECU", "GER"],
    ],
    "F": [
        ["NED", "JAP"],
        ["SWE", "TUN"],
        ["NED", "SWE"],
        ["TUN", "JAP"],
        ["TUN", "NED"],
        ["JAP", "SWE"],
    ],
    "G": [
        ["BEL", "EGY"],
        ["IRN", "NZL"],
        ["BEL", "IRN"],
        ["NZL", "EGY"],
        ["EGY", "IRN"],
        ["NZL", "BEL"],
    ],
}


def load_elo_per_team():

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
    logger.info(f"Elo ratings loaded from file: {elo_tsv}")


def load_fifa_code_to_alpha_2():
    fifa_member_associations = working_dir.joinpath("fifa-member-associations-fixed.csv")
    if not fifa_member_associations.is_file():
        logger.info(
            f"Downloading FIFA member associations file: {fifa_member_associations}"
        )
        with requests.get(
            "https://raw.githubusercontent.com/openpotato/fifa-codes/refs/heads/main/src/fifa-member-associations.csv"
        ) as r:
            r.raise_for_status()
            fifa_member_associations.write_bytes(r.content)
    with fifa_member_associations.open() as f:
        reader = csv.DictReader(f, dialect="excel")
        for row in filter(lambda x: x["Country.Iso3166.Alpha2Code"] in elo_per_team, reader):
            fifa_code_to_alpha_2[row["FIFA.Code"]] = row["Country.Iso3166.Alpha2Code"]
    logger.info(
        f"FIFA member associations loaded from file: {fifa_member_associations}"
    )


def load_fifa_code_to_name():
    iso_3166 = pathlib.Path("/usr/share/iso-codes/json/iso_3166-1.json")
    logger.info(f"Loading ISO 3166-1 codes from file: {iso_3166}")
    iso_3166_data = json.loads(
        pathlib.Path("/usr/share/iso-codes/json/iso_3166-1.json").read_text()
    )
    alpha_2_to_name = {}
    for item in filter(
        lambda x: x["alpha_2"] in fifa_code_to_alpha_2.values(), iso_3166_data["3166-1"]
    ):
        alpha_2_to_name[item["alpha_2"]] = item["name"]

    for fifa_code, alpha_2 in filter(lambda x: x[1] in alpha_2_to_name, fifa_code_to_alpha_2.items()):
        fifa_code_to_name[fifa_code] = alpha_2_to_name[alpha_2]
    logger.info("FIFA code to name mapping loaded from ISO 3166-1 data")


def main(args):
    logger.info(f"{working_dir = }")

    load_elo_per_team()
    load_fifa_code_to_alpha_2()

    # codes that are different on scorito.com
    fifa_code_to_alpha_2["BOS"] = "BA"
    fifa_code_to_alpha_2["CUR"] = "CW"
    fifa_code_to_alpha_2["JAP"] = "JP"
    
    # codes that are different on eloratings.net
    fifa_code_to_alpha_2["SCO"] = "SQ"

    load_fifa_code_to_name()

    # let's say these are complicated
    fifa_code_to_name["SCO"] = "Scotland"

    highest_elo = max(elo_per_team.values())
    logger.info(f"Highest Elo rating: {highest_elo}")
    lowest_elo = min(elo_per_team.values())
    logger.info(f"Lowest Elo rating: {lowest_elo}")
    max_diff = highest_elo - lowest_elo
    logger.info(f"Max Elo rating difference: {max_diff}")
    avg_goals = 2.69
    logger.info(f"Average goals: {avg_goals}")

    def calculate_win_probability(country1, country2):
        diff1 = elo_per_team[fifa_code_to_alpha_2[country1]] - lowest_elo
        diff2 = elo_per_team[fifa_code_to_alpha_2[country2]] - lowest_elo
        cupwinratio1 = diff1 / max_diff
        cupwinratio2 = diff2 / max_diff
        goals1 = round(cupwinratio1 / (cupwinratio1 + cupwinratio2) * avg_goals)
        goals2 = round(cupwinratio2 / (cupwinratio1 + cupwinratio2) * avg_goals)
        country1 = f"{fifa_code_to_name[country1]} ({country1})"
        country2 = f"{fifa_code_to_name[country2]} ({country2})"
        return {
            "country1": country1,
            "country2": country2,
            "winner": get_winner(goals1, goals2, country1, country2),
            "goals1": goals1,
            "goals2": goals2,
            "matchwinratio1": cupwinratio1 / (cupwinratio1 + cupwinratio2),
            "matchwinratio2": cupwinratio2 / (cupwinratio1 + cupwinratio2),
        }

    def get_winner(goals1, goals2, country1, country2):
        if goals1 == goals2:
            return "tie"
        elif goals1 < goals2:
            return country2
        else:
            return country1

    if args.group:
        for match in GROUPS[args.group.upper()]:
            print(calculate_win_probability(match[0], match[1]))
    else:
        print(calculate_win_probability(args.country1.upper(), args.country2.upper()))


if __name__ == "__main__":
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "country1", type=str, help="First country", default=argparse.SUPPRESS, nargs="?"
    )
    parser.add_argument(
        "country2",
        type=str,
        help="Second country",
        default=argparse.SUPPRESS,
        nargs="?",
    )
    parser.add_argument(
        "-g", "--group", type=str, help="Group", choices=[x.lower() for x in GROUPS]
    )
    args = parser.parse_args()
    main(args)
