#!/bin/bash

Ni=198
Nj=198
Nk=198
Step=20000
MaxN=5000000
MinIt=20
deltaX=10
procNums=(1 2 4 8 12 16 20 24 28 32)
procNum=1
Nis=(50 100 100 100 150 200 250 200 250 200)
Njs=(50 50 100 100 100 100 100 150 140 200)
Nks=(50 50 50 100 100 100 100 100 100 100)

for ((idx=0; idx<${#procNums[@]}; idx++)); do
    # Update values
    # Ni=$((${Nis[idx]}-2))
    # Nj=$((${Njs[idx]}-2))
    # Nk=$((${Nks[idx]}-2))
    Ni=${Nis[idx]}
    Nj=${Njs[idx]}
    Nk=${Nks[idx]}
    procNum=${procNums[idx]}
    # Step=$((MaxN*MinIt*procNum/((Ni+2)*(Nj+2)*(Nk+2))))
    Step=$((MaxN*MinIt*procNum/((Ni)*(Nj)*(Nk))))
    # Replace values in cavity3d.ini
    sed -i "s/^Ni\s*=\s*.*/Ni = $Ni/" cavity3d.ini
    sed -i "s/^Nj\s*=\s*.*/Nj = $Nj/" cavity3d.ini
    sed -i "s/^Nk\s*=\s*.*/Nk = $Nk/" cavity3d.ini
    sed -i "s/^thread_num\s*=\s*.*/thread_num = $procNum/" cavity3d.ini
    sed -i "s/^TotalStep\s*=\s*.*/TotalStep = $Step/" cavity3d.ini
    echo \n"------------iteration: $procNum-----------"\n

    for run in {1..5}; do
        ./cavity3d.exe
        sleep 5     # 5-second interval
    done
    # Update values
    # Ni=$((Ni + deltaX))
    # Nj=$((Nj + deltaX))
    # Nk=$((Nk + deltaX))
    # Step=$((MaxN*MinIt*x/((Ni+2)*(Nj+2)*(Nk+2))))
     # Replace values in cavity3d.ini
    # sed -i "s/^Ni\s*=\s*.*/Ni = $Ni/" cavity3d.ini
    # sed -i "s/^Nj\s*=\s*.*/Nj = $Nj/" cavity3d.ini
    # sed -i "s/^Nk\s*=\s*.*/Nk = $Nk/" cavity3d.ini

    sleep 5
done
