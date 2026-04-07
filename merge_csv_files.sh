#!/bin/bash
set -e  # exit on any error

RAW="data/raw/tennisabstract"
OUT="data/staging/tennisabstract"

# Create output directory if it doesn't exist
mkdir -p "$OUT"

get_longest_header_file() {
    local files=("$@")
    local best_file=""
    local best_cols=-1

    for f in "${files[@]}"; do
        [ -f "$f" ] || continue

        # Count columns in the header row
        local cols
        cols=$(head -n 1 "$f" | awk -F',' '{print NF}')

        if [ "$cols" -gt "$best_cols" ]; then
            best_cols="$cols"
            best_file="$f"
        fi
    done

    echo "$best_file"
}

combine() {
    local pattern="$1"
    local output="$2"
    local files=( $pattern )

    if [ ${#files[@]} -eq 0 ]; then
        echo "No files found for pattern: $pattern"
        return
    fi

    local header_file
    header_file=$(get_longest_header_file "${files[@]}")

    if [ -z "$header_file" ]; then
        echo "Could not determine header file for pattern: $pattern"
        return 1
    fi

    head -n 1 "$header_file" > "$output"

    for f in "${files[@]}"; do
        tail -n +2 "$f" >> "$output"
    done

    echo "Combined ${#files[@]} files into $output"
    echo "Header taken from: $header_file"
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

    local header_file
    header_file=$(get_longest_header_file "${files[@]}")

    if [ -z "$header_file" ]; then
        echo "Could not determine header file for patterns: ${patterns[*]}"
        return 1
    fi

    head -n 1 "$header_file" > "$output"

    for f in "${files[@]}"; do
        tail -n +2 "$f" >> "$output"
    done

    echo "Combined ${#files[@]} files into $output"
    echo "Header taken from: $header_file"
}

combine_slams_points_by_tournament_and_type() {
  local slams_raw_directory_name="tennis_slam_pointbypoint-master"
  local out_points_directory="${OUT}/points/slams"
  mkdir -p "${out_points_directory}"

  combine_multiple \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-ausopen-points.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-usopen-points.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-frenchopen-points.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-wimbledon-points.csv" \
  "${out_points_directory}/slams_points.csv"

  combine_multiple \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-ausopen-points-doubles.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-usopen-points-doubles.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-frenchopen-points-doubles.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-wimbledon-points-doubles.csv" \
  "${out_points_directory}/slams_points_doubles.csv"

  combine_multiple \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-ausopen-points-mixed.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-usopen-points-mixed.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-frenchopen-points-mixed.csv" \
  "${RAW}/${slams_raw_directory_name}/[0-9]*-wimbledon-points-mixed.csv" \
  "${out_points_directory}/slams_points_mixed.csv"
}

combine_charting_points() {
  local charting_points_directory_name="tennis_MatchChartingProject-master"
  local out_points_directory="${OUT}/points/charting"
  mkdir -p "${out_points_directory}"
  combine "${RAW}/${charting_points_directory_name}/charting-*-points-*.csv" "${out_points_directory}/charting_points.csv"
}

combine_rankings_by_league() {
  local out_matches_directory="${OUT}/rankings"
  LEAGUES=("atp" "wta")
  for league in "${LEAGUES[@]}"; do
    local raw_league_directory="${RAW}/tennis_${league}-master"
    local out_league_matches_directory="${out_matches_directory}/${league}"
    mkdir -p "${out_league_matches_directory}"
    combine "${raw_league_directory}/${league}_rankings_[0-9]*.csv" "${out_league_matches_directory}/${league}_rankings.csv"
  done
}

combine_slams_points_by_tournament_and_type
# combine_charting_points
# combine_rankings_by_league

### POINTS ###
# charting-{GENDER}-points-{YYYY}.csv
# charting-{GENDER}-points-to-{YYYY}.csv
# {YYYY}-{TOURNAMENT_TYPE}-points.csv
# {YYYY}-{TOURNAMENT_TYPE}-points-doubles.csv
# {YYYY}-{TOURNAMENT_TYPE}-points-mixed.csv