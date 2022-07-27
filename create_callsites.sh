if [ $# -le 1 ]; then
	echo "expecting one argument as input file. Usage: create_callsites.sh <file name>"
else
	if [ $# -eq 1 ]; then
		python3 addr2func.py ${1}.txt ${1}_translated_shorted
		python3 get_callsite.py ${1}_translated_shorted.txt >${1}_translated_shorted_callsite.txt
		python3 get_callsite.py ${1}_translated_shorted_3.txt >${1}_translated_shorted_3_callsite.txt
		python3 get_callsite.py ${1}_translated_shorted_5.txt >${1}_translated_shorted_5_callsite.txt
	else
		python3 addr2func.py ${1}.txt ${1}_translated_shorted_$2
		python3 get_callsite.py ${1}_translated_shorted_${2}.txt >${1}_translated_shorted_${2}_callsite.txt
		python3 get_callsite.py ${1}_translated_shorted_${2}_3.txt >${1}_translated_shorted_${2}_3_callsite.txt
		python3 get_callsite.py ${1}_translated_shorted_${2}_5.txt >${1}_translated_shorted_${2}_5_callsite.txt
	fi
fi
