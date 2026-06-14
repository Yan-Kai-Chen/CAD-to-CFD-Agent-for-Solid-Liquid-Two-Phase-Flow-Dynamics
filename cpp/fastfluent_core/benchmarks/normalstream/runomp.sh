#!/bin/bash

Ni=98
Nj=98
Nk=98
Step=20000
MaxN=1000000
MinIt=50
deltaX=10
procNum=(1 2 4 8 12 16 20 24 28 32 36 40 44)

# Update values
Ni=$((Ni))
Nj=$((Nj))
Nk=$((Nk))
Step=$((MaxN*MinIt/((Ni+2)*(Nj+2)*(Nk+2))))
# Replace values in cavity3d.ini
sed -i "s/^Ni\s*=\s*.*/Ni = $Ni/" cavity3d.ini
sed -i "s/^Nj\s*=\s*.*/Nj = $Nj/" cavity3d.ini
sed -i "s/^Nk\s*=\s*.*/Nk = $Nk/" cavity3d.ini
sed -i "s/^thread_num\s*=\s*.*/thread_num = 1/" cavity3d.ini
sed -i "s/^TotalStep\s*=\s*.*/TotalStep = $Step/" cavity3d.ini

for x in ${procNum[@]}; do
    Step=$((MaxN*MinIt*x/((Ni+2)*(Nj+2)*(Nk+2))))
    sed -i "s/^thread_num\s*=\s*.*/thread_num = $x/" cavity3d.ini
    sed -i "s/^TotalStep\s*=\s*.*/TotalStep = $Step/" cavity3d.ini
    echo \n"------------iteration: $x-----------"\n

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
