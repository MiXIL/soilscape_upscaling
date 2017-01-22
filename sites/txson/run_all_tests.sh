#!/bin/bash
for config in `ls configs/*cfg`
do
    for i in {1..10};
    do     
        echo python soilscape_upscaling_txson.py run_${i} ${config}
        python soilscape_upscaling_txson.py run_${i} ${config}
    done
done



