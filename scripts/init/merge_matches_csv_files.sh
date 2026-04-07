#!/bin/bash
set -e  # exit on any error

RAW="data/raw/tennisabstract"
OUT="data/staging/tennisabstract"

mkdir -p "$OUT"

# Function to combine CSVs (preserves header from first file)
combine() {
    local pattern="$1"
    local output="$2"
    files=( $pattern )
    if [ ${#files[@]} -eq 0 ]; then
        echo "No files found for pattern: $pattern"
        return
    fi
    head -n 1 "${files[0]}" > "$output"
    # Append the rest of the files without headers
    for f in "${files[@]}"; do
        tail -n +2 "$f" >> "$output"
    done
    echo "Combined ${#files[@]} files into $output"
}

combine_multiple() {
    local output="${@: -1}"
    local patterns=("${@:1:$#-1}")
    local files=()

    for pattern in "${patterns[@]}"; do
        for f in $pattern; do
            [ -e "$f" ] && files+=("$f")
        done
    done

    if [ ${#files[@]} -eq 0 ]; then
        echo "No files found for patterns: ${patterns[*]}"
        return
    fi

    head -n 1 "${files[0]}" > "$output"

    for f in "${files[@]}"; do
        tail -n +2 "$f" >> "$output"
    done

    echo "Combined ${#files[@]} files into $output"
}

combine_matches_by_league() {
  # ATP Matches: Singles 57 Files | Amateur 1 File | Doubles 21 Files | Futures 34 Files | Qual Chall 47 Files
  # WTA Matches: Singles 57 Files | Qual ITF 57 Files
  local out_matches_directory="${OUT}/matches"
  LEAGUES=("atp" "wta")
  for league in "${LEAGUES[@]}"; do
    local raw_league_directory="${RAW}/tennis_${league}-master"
    local out_league_matches_directory="${out_matches_directory}/${league}"
    mkdir -p "${out_league_matches_directory}"
    combine "${raw_league_directory}/${league}_matches_[0-9]*.csv" "${out_league_matches_directory}/${league}_matches.csv"

    case "${league}" in
      atp)
        combine "${raw_league_directory}/${league}_matches_amateur.csv"           "${out_league_matches_directory}/${league}_matches_amateur.csv"
        combine "${raw_league_directory}/${league}_matches_doubles_[0-9]*.csv"    "${out_league_matches_directory}/${league}_matches_doubles.csv"
        combine "${raw_league_directory}/${league}_matches_futures_[0-9]*.csv"    "${out_league_matches_directory}/${league}_matches_futures.csv"
        combine "${raw_league_directory}/${league}_matches_qual_chall_[0-9]*.csv" "${out_league_matches_directory}/${league}_matches_qual_chall.csv"
    ;;
      wta) combine "${raw_league_directory}/${league}_matches_qual_itf_[0-9]*.csv" "${out_league_matches_directory}/${league}_matches_qual_itf.csv";;
    esac
  done
}

combine_slams_matches_by_tournament_and_type() {
  local slams_raw_directory_name="tennis_slam_pointbypoint-master"
  local out_matches_directory="${OUT}/matches/slams"
  mkdir -p "${out_matches_directory}"
  combine_multiple \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-ausopen-matches.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-usopen-matches.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-frenchopen-matches.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-wimbledon-matches.csv" \
  "${out_matches_directory}/slams_matches.csv"

  combine_multiple \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-ausopen-matches-doubles.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-usopen-matches-doubles.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-frenchopen-matches-doubles.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-wimbledon-matches-doubles.csv" \
  "${out_matches_directory}/slams_matches_doubles.csv"

  combine_multiple \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-ausopen-matches-mixed.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-usopen-matches-mixed.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-frenchopen-matches-mixed.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-wimbledon-matches-mixed.csv" \
  "${out_matches_directory}/slams_matches_mixed.csv"
}

# combine_matches_by_league
combine_slams_matches_by_tournament_and_type


### PLAYERS
# atp_players.csv
# wta_players.csv
# mwplayerlist.js

### MATCHES ###
# charting-{GENDER}-matches.csv
# atp_matches_YYYY.csv
# atp_matches_doubles_YYYY.csv
# atp_matches_futures_YYYY.csv
# atp_matches_qual_chall_YYYY.csv
# atp_matches_amateur.csv 
# wta_matches_YYYY.csv
# wta_matches_qual_itf_YYYY.csv
# {YYYY}-{TOURNAMENT_TYPE}-matches.csv
# {YYYY}-{TOURNAMENT_TYPE}-matches-doubles.csv
# {YYYY}-{TOURNAMENT_TYPE}-matches-mixed.csv

### POINTS ###
# charting-{GENDER}-points-{YYYY}.csv
# charting-{GENDER}-points-to-{YYYY}.csv
# {YYYY}-{TOURNAMENT_TYPE}-points.csv
# {YYYY}-{TOURNAMENT_TYPE}-points-doubles.csv
# {YYYY}-{TOURNAMENT_TYPE}-points-mixed.csv


### RANKINGS ###
# atp_rankings_{YY}.csv
# atp_rankings_current.csv
# wta_rankings_{YY}.csv
# wta_rankings_current.csv
