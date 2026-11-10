#! /bin/bash

py_files=$(find . -name "*.py")
py_proj_header="# Copyright IBM 202[5-9]"
py_qiskit_header="# This code is a Qiskit project."

result=0
for file in $py_files
do
    first_line=$(head -n 1 ${file})
    if [[ $first_line != $py_proj_header ]] && [[ $first_line != $py_qiskit_header ]]
    then
        echo "$file has wrong header: $first_line"
        result=1
    fi
done

exit $result
