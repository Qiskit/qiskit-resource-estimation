#! /bin/bash

files=$(find . -name "*.py")
header="# Copyright IBM 202[5-9]"

result=0
for file in $files
do
    first_line=$(head -n 1 ${file})
    if [[ $first_line != $header ]]
    then
        echo "$file has wrong header: $first_line"
        result=1
    fi
done

exit $result
