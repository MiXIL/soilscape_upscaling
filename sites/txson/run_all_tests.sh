#!/bin/bash

config=$1
for i in {1..5};
do     
    echo python soilscape_upscaling_txson.py run_${i} ${config}
    python soilscape_upscaling_txson.py run_${i} ${config}
done



