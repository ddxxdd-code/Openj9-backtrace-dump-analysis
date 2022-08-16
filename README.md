# Openj9-backtrace-dump-analysis
Analysis scripts for translating and aggregating heap allocation callsites from OpenJ9

Run `create_callsite.sh` to get callsites.

The callsites will be generated as follows:

create_callsite.sh accepts one or two arguments.

`./create_callsite.sh <input_name> <postfix>[optional]`

This will run translation `addr2func.py` on `<input_name>.txt` and pass outputs to `<input_name>_translated_shorted[_<postfix>].txt`

Then will run analysis program `get_callsite.py` to get callsites and store in the file `<input_name>_translated_shorted[_<postfix>]_callsite.txt`

Requirement for running backtrace_analyzer.py: need python of version 3.7+
