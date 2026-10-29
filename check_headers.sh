#! /bin/bash

py_files=$(find . -name "*.py")
py_proj_header="# Copyright IBM 202[5-9]"
py_qiskit_header="# This code is a Qiskit project."

rs_files=$(find crates/ -name "*.rs")
rs_proj_header="// Copyright IBM 202[5-9]"
rs_qiskit_header="// This code is part of Qiskit."

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

for file in $rs_files
do
    first_line=$(head -n 1 ${file})
    if [[ $first_line != $rs_proj_header ]] && [[ $first_line != $rs_qiskit_header ]]
    then
        echo "$file has wrong header: $first_line"
        result=1
    fi
done

exit $result
