#!/usr/bin/env bash

# format_python.sh
# Format, lint and run coverity on python files using black, coverity, flake8, and/or pylint.

# Add Coverity bin to path
PATH=$PATH:/var/tmp/coverity/bin/

# Settings.
MAX_LINE_LEN=100 # used by black and flake8

# Ignoring these flake8 warnings:
# E402: module level import not at top of file
# W503: line break before binary operator
# E203 whitespace before ':'
#      - black handles this
FLAKE8_IGNORE_CODES='E402,W503,E203'

# Ignoring these pylint warnings:
# C0301: line too long
#      - line length handled by black and flake8
# C0302: too many lines in module
# C0330: wrong hanging indent
#     - pylint doesn't like black's formatting style
# R0902: too many instance attributes
# R0904: too many public methods in class
# R0913: too many arguments
# W0703: catching too general exception
# C0413: used when code and imports are mixed
# W0707: 'raise' missing 'from'
# W1514: Using open without explicitly specifying an encoding
PYLINT_IGNORE_CODES='C0301,C0302,C0330,R0902,R0904,R0913,W0703,C0413,W0707,W1514'

DEFAULT_PROGRAMS='black,flake8,pylint'

# Variable is only used when script is invoked in read-only mode
did_fail="0"

# Coverity Analysis directory
COV_ANALYSIS_DIR="./data-coverity"
COV_KEY_PATH="$HOME/.coverity/authkeys/ak-coverity.viasat.com-443"


check_files_exist(){
    file_paths="$@"
    is_error=0
    if [ ! "$file_paths" ]; then
        echo "[ERROR] No files given" >&2
        is_error=1
    fi
    for file_path in $file_paths; do
        if [ ! -f "$file_path" ]; then
            echo "[ERROR] Cannot find file \"$file_path\"" >&2
            is_error=1
        fi
    done
    return $is_error
}


lint_analyze_python_files(){
    trap 'did_fail=$?' ERR
    file_paths="$@"
    for file_path in $file_paths; do
        echo "linting and analyzing $file_path"
        if [[ "${file_path##*\.}" != *"py"* ]]; then
            echo "[WARNING] non-python file \"$file_path\"" >&2
        fi
        # Fix path for Cygwin on Windows.
        if [[ "$OS" == *"Windows"* ]] && command -v cygpath 2>&1 1>/dev/null; then
            file_path="$(cygpath "$file_path")"
        fi
        # Format, lint and run coverity file(s).
        if [[ "$programs" == *"b"* ]]; then
            echo '[black]'
            if [[ "$mode" == "read" ]]; then
                black --check -q -l $MAX_LINE_LEN "$file_path" 2>&1
                exit_code=$?
                if [ "$exit_code" != "0" ]; then
                    echo "\"$file_path\" failed black formatting checks"
                fi
            else
                black -q -l $MAX_LINE_LEN "$file_path" 2>&1
            fi
        fi
        if [[ "$programs" == *"f"* ]]; then
            echo '[flake8]'
            flake8 --ignore=$FLAKE8_IGNORE_CODES --max-line-length=$MAX_LINE_LEN "$file_path" 2>&1
        fi
        if [[ "$programs" == *"p"* ]]; then
            echo '[pylint]'
            if [[ "$mode" == "read" ]]; then
                pylint -d "$PYLINT_IGNORE_CODES" "$file_path"
            else
                pylint -d "$PYLINT_IGNORE_CODES" "$file_path" \
                    | grep -v "\------------------------------------------------------------------" \
                    | tr -s $'\n' \
                    | grep -vE "^$"
            fi
        fi
        if [[ "$programs" == *",c"* ]]; then
            echo '[coverity]'
            # Set up coverity for the user if needed
            if [ $set_up_cov -eq 1 ]; then
                rm -rf "$COV_ANALYSIS_DIR"
                if [ ! -f "$key_file" ]; then
                    # no auth key, create it on setup
                    cov-run-desktop --setup
                else
                    cov-run-desktop --auth-key-file "$key_file" --setup
                fi
                # we only need to do this once so avoid running for each file
                set_up_cov=0
            fi
            cov-run-desktop --auth-key-file "$key_file" --exit1-if-defects true "$file_path"
        fi
        echo
    done
}


format_python(){
    usage_text="Usage: format_python.sh [-m mode] [-a auth-key-file] [-s] [-p programs] FILE_PATH_1 FILE_PATH_2 ...
    Format, lint and run Coverity on python files.
    black, flake8, and pylint are required: pip install black flake8 pylint
    For coverity setup: Run 'format_python.sh -s -p c some_file.py' in the same directory as coverity.conf.
                        Run the setup any time coverity.conf has changed OR a file has been added/removed/renamed
                        to/from the Modot-Tools repo.
                        This will create $COV_KEY_PATH
                        that is used in running coverity analysis.

      -p PROGRAMS      [optional] comma-separated list of programs to use
                         will NOT change the order in which they're run (black --> flake8 --> pylint -> coverity)
                         defaults to \"$DEFAULT_PROGRAMS\"
                         choices: black, coverity, flake8, and/or pylint (first letter abbreviations allowed)
                         examples: \"b,c,f,p\" or \"black,coverity,flake8,pylint\" or \"b\"
      -m mode          [optional] parameter whether to format a file. If \"read\" is used
                         this script will exit with 1 on any files that require formatting, linting or coverity defects.
                         defaults to write
                         choices: read or write
      -a auth-key-file [optional] file that will be used by Coverity to authenticate with server for analysis.
                         Parameter is used when running Coverity analysis.
                         defaults to $HOME/.coverity/authkeys/ak-coverity.viasat.com-443
      -s               [optional] flag whether to remove the $COV_ANALYSIS_DIR and run
                         cov-run-desktop --setup and create the auth-key for coverity
                         stored in $COV_KEY_PATH"
    programs="${DEFAULT_PROGRAMS}"
    options='h:p:m:c:a:s'
    mode="write"
    key_file="$COV_KEY_PATH"
    set_up_cov=0
    while getopts $options option; do
        case "$option" in
            h)
                echo -e "$usage_text"
                return 0
            ;;
            p)
                programs="$OPTARG"
                if [[ "$programs" != *[bcfp]* ]]; then
                    echo "[ERROR] Unrecognized programs: \"$programs\""
                    return 1
                fi
            ;;
            m)
                mode="$OPTARG"
                if [[ "$mode" != "read" ]] && [[ "$mode" != "write" ]]; then
                    echo "[ERROR] Unrecognized mode: \"$mode\""
                    return 1
                fi
            ;;
            a)
                key_file="$OPTARG"
                check_files_exist "$key_file"
            ;;
            s)
                set_up_cov=1
            ;;
            *)
                echo -e "$usage_text"
                return 1
            ;;
        esac
    done
    shift $((OPTIND-1))
    file_paths="$@"
    check_files_exist "$file_paths" || exit 1
    lint_analyze_python_files "$file_paths"
    echo done
    return "$did_fail"
}


format_python "$@"
