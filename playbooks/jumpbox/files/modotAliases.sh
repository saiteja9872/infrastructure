# MoDOT owned aliases for Modem-Tool
alias p3='source /var/tmp/modot_venv/bin/activate'
alias mtool='setfacl -R -m u:sshproxy:rwx ~/ > /dev/null 2>&1 ; source /var/tmp/modot_venv/bin/activate; sudo -E PATH=$PATH -u sshproxy /var/tmp/modot_venv/bin/python /var/tmp/modot_tools/modem_tool/modem_tool.py'
alias modem_key_ssh='sudo -u sshproxy /var/tmp/modot_tools/modem_key_ssh'
alias modem_key_scp='setfacl -R -m u:sshproxy:rwx ~/ > /dev/null 2>&1 ; sudo -u sshproxy /var/tmp/modot_tools/modem_key_scp -c `whoami`'
# these aliases include setfacl because sshproxy needs write and execute access to create the
# ~/.mtool/logs/mtool_run.log file in the user's home directory and write the mtool logs to it
# while mtool is running. sshproxy needs read access so that, when it runs the put_file action
# in mtool or the modem_key_scp script, it has permission to SCP the user's requested file to
# a modem. we call it every time the user runs mtool in case the user has put a new file on the
# jumpbox (presumably a file that it plans to SCP to a modem) since they last ran mtool, or in
# case the user has deleted the mtool_run.log file or its directory since mtool last ran.

# MoDOT owned functions for using Modem-Tool
ut_ssh() { mtool -a ssh -M "$1" -i; }
get_bb() { mtool -a get_bb -M "$1" -i; }
run_cmd() { mtool -a run_commands -C "$1" -M "$2" -i; }
get_ip() { mtool -a get_ip -M "$1" -i; }
get_file() { mtool -a get_file -r "$1" -M "$2" -i; }
put_file() { mtool -a put_file -l "$1" -M "$2" -i; }

m3tool() { mtool -B; }
m3_ssh() { mtool -a ssh -M "$1" -B -i; }
m3_get_bb() { mtool -a get_bb -M "$1" -B -i; }
m3_run_cmd() { mtool -a run_commands -C "$1" -M "$2" -B -i; }
m3_get_ip() { mtool -a get_ip -M "$1" -B -i; }
m3_get_file() { mtool -a get_file -r "$1" -M "$2" -B -i; }
m3_put_file() { mtool -a put_file -l "$1" -M "$2" -B -i; }

# For use on PreProd JB
# MoDOT owned aliases for Coverity
PATH=$PATH:/var/tmp/coverity/bin/


# MoDOT owned function to run Coverity on all modified or added Python files
# in a branch. Needs to be in the same directory as coverity.conf and in a git directory
# and the first argument is the path to your key file to use to authenticate with Coverity.
# Will run cov-run-desktop --setup in the event it was not run before.
# Note: Not used for scripts but available for personal use.
runCovOnBranch() {
    cov-run-desktop --analyze-scm-modified  --analyze-untracked-files true  --restrict-untracked-file-regex "[.]py"
     if [ $? -eq 2 ]; then
        echo "You need to run cov-run-desktop --setup first. Make sure you are in the correct directory"
        echo "Running setup for you now..."
        sleep 1
        if cov-run-desktop --setup; then
            echo "cov-run-desktop setup complete. Please re-run runCovOnBranch"
        else
            echo "cov-run-desktop setup failed. Please check the wiki for more information."
        fi
    fi
}
