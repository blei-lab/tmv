#!/bin/bash

newfile="stylingsbs.css"

cp -f styling.css $newfile

sed -i "s/#b5caf7/#FFE5CC/g" $newfile
sed -i "s/#D5DFF5/#FFE5CC/g" $newfile
sed -i "s/#799FF2/#F7AB31/g" $newfile
sed -i "s/#B5CAF7/#FFE5CC/g" $newfile
sed -i "s/#416DCC/#416DCC/g" $newfile
sed -i "s/#0050FF/#0050FF/g" $newfile
sed -i "s/#12337A/#12337A/g" $newfile
sed -i "s/#363C4A/#363C4A/g" $newfile
sed -i "s/#628AE3/#628AE3/g" $newfile
sed -i "s/#2E58B3/#2E58B3/g" $newfile
sed -i "s/#547DD6/#547DD6/g" $newfile
sed -i "s/#f2f2f2/#f2f2f2/g" $newfile
sed -i "s/#b3cde3/#b3cde3/g" $newfile
sed -i "s/#fbb4ae/#fbb4ae/g" $newfile
sed -i "s/#DCDCDC/#DCDCDC/g" $newfile
sed -i "s/#2196F3/#2196F3/g" $newfile
sed -i "s/#777/#777/g" $newfile
sed -i "s/#ddd/#ddd/g" $newfile
sed -i "s/#FFE5CC/#fed9a6/g" $newfile


#sed -i "s/#/#/g" $newfile

sed -i "s/blue/orange/g" $newfile
sed -i "s/goldenrod/goldenrod/g" $newfile
