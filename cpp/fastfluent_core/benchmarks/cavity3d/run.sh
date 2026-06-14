#!/bin/bash

Ni=28
Nj=28
Nk=28
Step=20000
MaxN=8000000
MinIt=20
deltaX=10

# Update values
Ni=$((Ni))
Nj=$((Nj))
Nk=$((Nk))
Step=$((MaxN*MinIt/((Ni+2)*(Nj+2)*(Nk+2))))
# Replace values in cavity3d.ini
sed -i "s/^Ni\s*=\s*.*/Ni = $Ni/" cavity3d.ini
sed -i "s/^Nj\s*=\s*.*/Nj = $Nj/" cavity3d.ini
sed -i "s/^Nk\s*=\s*.*/Nk = $Nk/" cavity3d.ini
sed -i "s/^TotalStep\s*=\s*.*/TotalStep = $Step/" cavity3d.ini

for x in {1..18}; do
    echo \n"------------iteration: $x-----------"\n
    for run in {1..5}; do
        ./cavity3d.exe
        sleep 5     # 5-second interval
    done
    # Update values
    Ni=$((Ni + deltaX))
    Nj=$((Nj + deltaX))
    Nk=$((Nk + deltaX))
    Step=$((MaxN*MinIt/((Ni+2)*(Nj+2)*(Nk+2))))
     # Replace values in cavity3d.ini
    sed -i "s/^Ni\s*=\s*.*/Ni = $Ni/" cavity3d.ini
    sed -i "s/^Nj\s*=\s*.*/Nj = $Nj/" cavity3d.ini
    sed -i "s/^Nk\s*=\s*.*/Nk = $Nk/" cavity3d.ini
    sed -i "s/^TotalStep\s*=\s*.*/TotalStep = $Step/" cavity3d.ini
    sleep 5
done
