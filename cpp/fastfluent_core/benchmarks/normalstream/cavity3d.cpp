/* This file is part of FreeLB
 *
 * Copyright (C) 2024 Yuan Man
 * E-mail contact: ymmanyuan@outlook.com
 * The most recent progress of FreeLB will be updated at
 * <https://github.com/zdxying/FreeLB>
 *
 * FreeLB is free software: you can redistribute it and/or modify it under the terms of
 * the GNU General Public License as published by the Free Software Foundation, either
 * version 3 of the License, or (at your option) any later version.
 *
 * FreeLB is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 * without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 * PURPOSE. See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along with FreeLB. If
 * not, see <https://www.gnu.org/licenses/>.
 *
 */

// cavblock3d.cpp

// Lid-driven cavity flow 3d
// this is a benchmark for the freeLB

// the top wall is set with a constant velocity,
// while the other walls are set with a no-slip boundary condition
// Bounce-Back-like method is used:
// Bounce-Back-Moving-Wall method for the top wall
// Bounce-Back method for the other walls

// block data structure is used

#include "freelb.h"
#include "freelb.hh"


// using T = FLOAT;
using T = float;
using LatSet = D3Q19<T>;

// normal pop field using
template <typename T, unsigned int q>
using NPOPSOA = GenericField<GenericArray<T>, POPBase<q>>;
template <typename T, unsigned int q>
using NPOPAOS = GenericField<GenericArray<Vector<T,q>>, POPBase<1>>;

// cell interface for block lattice NPOPSOA
template <typename T, typename LatSet, typename TypePack>
class NCellSOA {
 protected:
  // global cell index to access field data and distribution functions
  std::size_t Id;
  // reference to lattice
  BlockLattice<T, LatSet, TypePack>& Lat;

 public:
  using FloatType = T;
  using LatticeSet = LatSet;
  using BLOCKLATTICE = BlockLattice<T, LatSet, TypePack>;
  using GenericRho = typename BLOCKLATTICE::GenericRho;

  NCellSOA(std::size_t id, BlockLattice<T, LatSet, TypePack>& lat)
      : Id(id), Lat(lat) {}

  // get population
  const T& operator[](int i) const { return Lat.template getField<NPOPSOA<T, LatSet::q>>().getField(i)[Id]; }
  T& operator[](int i) { return Lat.template getField<NPOPSOA<T, LatSet::q>>().getField(i)[Id]; }

  template <typename FieldType, unsigned int i = 0>
  auto& get() {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().template get<i>(Id);
    } else {
      return Lat.template getField<FieldType>().template get<i>();
    }
  }
  template <typename FieldType, unsigned int i = 0>
  const auto& get() const {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().template get<i>(Id);
    } else {
      return Lat.template getField<FieldType>().template get<i>();
    }
  }
  template <typename FieldType>
  auto& get(unsigned int i) {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().get(Id, i);
    } else {
      return Lat.template getField<FieldType>().get(i);
    }
  }
  template <typename FieldType>
  const auto& get(unsigned int i) const {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().get(Id, i);
    } else {
      return Lat.template getField<FieldType>().get(i);
    }
  }

  template <typename FieldType>
  auto& getField() {
    return Lat.template getField<FieldType>();
  }
  template <typename FieldType>
  const auto& getField() const {
    return Lat.template getField<FieldType>();
  }

  template <typename FieldType>
  static constexpr bool hasField() {
    return BLOCKLATTICE::template hasField<FieldType>();
  }

  Cell<T, LatSet, TypePack> getNeighbor(unsigned int i) const {
    return Cell<T, LatSet, TypePack>(Id + Lat.getDelta_Index()[i], Lat);
  }
  Cell<T, LatSet, TypePack> getNeighbor(const Vector<int, LatSet::d>& direction) const {
    return Cell<T, LatSet, TypePack>(Id + direction * Lat.getProjection(), Lat);
  }

  void setId(std::size_t id) { Id = id; }
  // ++id
  void operator++() { ++Id; }

  std::size_t getId() const { return Id; }
  std::size_t getNeighborId(unsigned int i) const { return Id + Lat.getDelta_Index()[i]; }

  // get population before streaming
  T& getPrevious(int i) const {
    return Lat.template getField<POP<T, LatSet::q>>().getField(i).getPrevious(Id);
  }
  // Lat.getOmega()
  inline T getOmega() const { return Lat.getOmega(); }
  // Lat.get_Omega()
  inline T get_Omega() const { return Lat.get_Omega(); }
  // Lat.getfOmega()
  inline T getfOmega() const { return Lat.getfOmega(); }
};

// cell interface for block lattice NPOPAOS
template <typename T, typename LatSet, typename TypePack>
class NCellAOS {
 protected:
  // global cell index to access field data and distribution functions
  std::size_t Id;
  // reference to lattice
  BlockLattice<T, LatSet, TypePack>& Lat;

 public:
  using FloatType = T;
  using LatticeSet = LatSet;
  using BLOCKLATTICE = BlockLattice<T, LatSet, TypePack>;
  using GenericRho = typename BLOCKLATTICE::GenericRho;

  NCellAOS(std::size_t id, BlockLattice<T, LatSet, TypePack>& lat)
      : Id(id), Lat(lat) {}

  // get population
  const T& operator[](int i) const { return Lat.template getField<NPOPAOS<T, LatSet::q>>().getField(0)[Id][i]; }
  T& operator[](int i) { return Lat.template getField<NPOPAOS<T, LatSet::q>>().getField(0)[Id][i]; }

  template <typename FieldType, unsigned int i = 0>
  auto& get() {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().template get<i>(Id);
    } else {
      return Lat.template getField<FieldType>().template get<i>();
    }
  }
  template <typename FieldType, unsigned int i = 0>
  const auto& get() const {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().template get<i>(Id);
    } else {
      return Lat.template getField<FieldType>().template get<i>();
    }
  }
  template <typename FieldType>
  auto& get(unsigned int i) {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().get(Id, i);
    } else {
      return Lat.template getField<FieldType>().get(i);
    }
  }
  template <typename FieldType>
  const auto& get(unsigned int i) const {
    if constexpr (FieldType::isField) {
      return Lat.template getField<FieldType>().get(Id, i);
    } else {
      return Lat.template getField<FieldType>().get(i);
    }
  }

  template <typename FieldType>
  auto& getField() {
    return Lat.template getField<FieldType>();
  }
  template <typename FieldType>
  const auto& getField() const {
    return Lat.template getField<FieldType>();
  }

  template <typename FieldType>
  static constexpr bool hasField() {
    return BLOCKLATTICE::template hasField<FieldType>();
  }

  Cell<T, LatSet, TypePack> getNeighbor(unsigned int i) const {
    return Cell<T, LatSet, TypePack>(Id + Lat.getDelta_Index()[i], Lat);
  }
  Cell<T, LatSet, TypePack> getNeighbor(const Vector<int, LatSet::d>& direction) const {
    return Cell<T, LatSet, TypePack>(Id + direction * Lat.getProjection(), Lat);
  }

  void setId(std::size_t id) { Id = id; }
  // ++id
  void operator++() { ++Id; }

  std::size_t getId() const { return Id; }
  std::size_t getNeighborId(unsigned int i) const { return Id + Lat.getDelta_Index()[i]; }

  // get population before streaming
  T& getPrevious(int i) const {
    return Lat.template getField<POP<T, LatSet::q>>().getField(i).getPrevious(Id);
  }
  // Lat.getOmega()
  inline T getOmega() const { return Lat.getOmega(); }
  // Lat.get_Omega()
  inline T get_Omega() const { return Lat.get_Omega(); }
  // Lat.getfOmega()
  inline T getfOmega() const { return Lat.getfOmega(); }
};

template <typename T, typename LatSet, typename TypePack>
void NStreamSOA (BlockLatticeManager<T,LatSet,TypePack>& LatMan) {
  auto& BFM = LatMan.template getField<NPOPSOA<T, LatSet::q>>();
  #pragma omp parallel for num_threads(Thread_Num)
  for (std::size_t idx = 0; idx < LatMan.getBlockLats().size(); ++idx) {
  auto& blocklat = LatMan.getBlockLat(idx);
  const int Nx = blocklat.getNx();
  const int Ny = blocklat.getNy();
  const int Nz = blocklat.getNz();
  const int NxNy = Nx * Ny;
  for (unsigned int i = 1; i < LatSet::q; i+=2) {

    const int zstart = latset::c<LatSet>(i)[2] > 0 ? Nz - 1 : 0;
    const int zend = zstart == 0 ? Nz - 1 : 0;
    const int zdelta = zstart == 0 ? 1 : -1;
    const int ystart = latset::c<LatSet>(i)[1] > 0 ? Ny - 1 : 0;
    const int yend = ystart == 0 ? Ny - 1 : 0;
    const int ydelta = ystart == 0 ? 1 : -1;
    const int xstart = latset::c<LatSet>(i)[0] > 0 ? Nx - 1 : 0;
    const int xend = xstart == 0 ? Nx - 1 : 0;
    const int xdelta = xstart == 0 ? 1 : -1;

    const int deltaIdx = blocklat.getDelta_Index()[i];

    auto& pop = BFM.getBlockField(idx).getField(i);
    for (int z = zstart; z != zend; z += zdelta) {
      for (int y = ystart; y != yend; y += ydelta) {
        for (int x = xstart; x != xend; x += xdelta) {
          std::size_t id = x + y * Nx + z * NxNy;
          std::size_t idn = id - deltaIdx;
          pop[id] = pop[idn];
        }
      }
    }
    const int zstartx = latset::c<LatSet>(i)[2] < 0 ? Nz - 1 : 0;
    const int zendx = zstartx == 0 ? Nz - 1 : 0;
    const int zdeltax = zstartx == 0 ? 1 : -1;
    const int ystartx = latset::c<LatSet>(i)[1] < 0 ? Ny - 1 : 0;
    const int yendx = ystartx == 0 ? Ny - 1 : 0;
    const int ydeltax = ystartx == 0 ? 1 : -1;
    const int xstartx = latset::c<LatSet>(i)[0] < 0 ? Nx - 1 : 0;
    const int xendx = xstartx == 0 ? Nx - 1 : 0;
    const int xdeltax = xstartx == 0 ? 1 : -1;

    auto& popx = BFM.getBlockField(idx).getField(i+1);
    for (int z = zstartx; z != zendx; z += zdeltax) {
      for (int y = ystartx; y != yendx; y += ydeltax) {
        for (int x = xstartx; x != xendx; x += xdeltax) {
          std::size_t id = x + y * Nx + z * NxNy;
          std::size_t idn = id + deltaIdx;
          popx[id] = popx[idn];
        }
      }
    }
  }

  }
}

template <typename T, typename LatSet, typename TypePack>
void NStreamAOS (BlockLatticeManager<T,LatSet,TypePack>& LatMan) {
  auto& BFM = LatMan.template getField<NPOPAOS<T, LatSet::q>>();
  #pragma omp parallel for num_threads(Thread_Num)
  for (std::size_t idx = 0; idx < LatMan.getBlockLats().size(); ++idx) {
  auto& blocklat = LatMan.getBlockLat(idx);
  const int Nx = blocklat.getNx();
  const int Ny = blocklat.getNy();
  const int Nz = blocklat.getNz();
  const int NxNy = Nx * Ny;
  auto& pop = BFM.getBlockField(idx).getField(0);
  // boundary stream
  // z = 0
  for (int y = 0; y < Ny - 1; ++y) {
    for (int x = 0; x < Nx - 1; ++x) {
      std::size_t id = x + y * Nx;
      for (unsigned int i = 1; i < LatSet::q; i+=2) {
        T temp = pop[id][i];
        pop[id][i] = pop[id][i+1];
        pop[id][i+1] = temp;
      }
    }
  }
  // z = Nz - 1
  for (int y = 0; y < Ny - 1; ++y) {
    for (int x = 0; x < Nx - 1; ++x) {
      std::size_t id = x + y * Nx + (Nz - 1) * NxNy;
      for (unsigned int i = 1; i < LatSet::q; i+=2) {
        T temp = pop[id][i];
        pop[id][i] = pop[id][i+1];
        pop[id][i+1] = temp;
      }
    }
  }
  // y = 0
  for (int z = 0; z < Nz - 1; ++z) {
    for (int x = 0; x < Nx - 1; ++x) {
      std::size_t id = x + z * NxNy;
      for (unsigned int i = 1; i < LatSet::q; i+=2) {
        T temp = pop[id][i];
        pop[id][i] = pop[id][i+1];
        pop[id][i+1] = temp;
      }
    }
  }
  // y = Ny - 1
  for (int z = 0; z < Nz - 1; ++z) {
    for (int x = 0; x < Nx - 1; ++x) {
      std::size_t id = x + (Ny - 1) * Nx + z * NxNy;
      for (unsigned int i = 1; i < LatSet::q; i+=2) {
        T temp = pop[id][i];
        pop[id][i] = pop[id][i+1];
        pop[id][i+1] = temp;
      }
    }
  }
  // x = 0
  for (int z = 0; z < Nz - 1; ++z) {
    for (int y = 0; y < Ny - 1; ++y) {
      std::size_t id = y * Nx + z * NxNy;
      for (unsigned int i = 1; i < LatSet::q; i+=2) {
        T temp = pop[id][i];
        pop[id][i] = pop[id][i+1];
        pop[id][i+1] = temp;
      }
    }
  }
  // x = Nx - 1
  for (int z = 0; z < Nz - 1; ++z) {
    for (int y = 0; y < Ny - 1; ++y) {
      std::size_t id = (Nx - 1) + y * Nx + z * NxNy;
      for (unsigned int i = 1; i < LatSet::q; i+=2) {
        T temp = pop[id][i];
        pop[id][i] = pop[id][i+1];
        pop[id][i+1] = temp;
      }
    }
  }

  // bulk stream
  for (int z = 1; z < Nz - 1; ++z) {
    for (int y = 1; y < Ny - 1; ++y) {
      for (int x = 1; x < Nx - 1; ++x) {
        std::size_t id = x + y * Nx + z * NxNy;
        for (unsigned int i = 1; i < LatSet::q; i+=2) {
          std::size_t idn = id + blocklat.getDelta_Index()[i];
          T temp = pop[id][i];
          pop[id][i] = pop[id][i+1];
          pop[id][i+1] = pop[idn][i];
          pop[idn][i] = temp;
        }
      }
    }
  }
}
}

template <typename T, typename LatSet, typename TypePack>
void NStreamAOS_SOAlike (BlockLatticeManager<T,LatSet,TypePack>& LatMan) {
  auto& BFM = LatMan.template getField<NPOPAOS<T, LatSet::q>>();
  auto& blocklat = LatMan.getBlockLat(0);
  const int Nx = blocklat.getNx();
  const int Ny = blocklat.getNy();
  const int Nz = blocklat.getNz();
  const int NxNy = Nx * Ny;
  auto& pop = BFM.getBlockField(0).getField(0);

  for (unsigned int i = 1; i < LatSet::q; i+=2) {

    const int zstart = latset::c<LatSet>(i)[2] > 0 ? Nz - 1 : 0;
    const int zend = zstart == 0 ? Nz - 1 : 0;
    const int zdelta = zstart == 0 ? 1 : -1;
    const int ystart = latset::c<LatSet>(i)[1] > 0 ? Ny - 1 : 0;
    const int yend = ystart == 0 ? Ny - 1 : 0;
    const int ydelta = ystart == 0 ? 1 : -1;
    const int xstart = latset::c<LatSet>(i)[0] > 0 ? Nx - 1 : 0;
    const int xend = xstart == 0 ? Nx - 1 : 0;
    const int xdelta = xstart == 0 ? 1 : -1;

    const int deltaIdx = blocklat.getDelta_Index()[i];

    for (int z = zstart; z != zend; z += zdelta) {
      for (int y = ystart; y != yend; y += ydelta) {
        for (int x = xstart; x != xend; x += xdelta) {
          std::size_t id = x + y * Nx + z * NxNy;
          std::size_t idn = id - deltaIdx;
          pop[id][i] = pop[idn][i];
        }
      }
    }
    const int zstartx = latset::c<LatSet>(i)[2] < 0 ? Nz - 1 : 0;
    const int zendx = zstartx == 0 ? Nz - 1 : 0;
    const int zdeltax = zstartx == 0 ? 1 : -1;
    const int ystartx = latset::c<LatSet>(i)[1] < 0 ? Ny - 1 : 0;
    const int yendx = ystartx == 0 ? Ny - 1 : 0;
    const int ydeltax = ystartx == 0 ? 1 : -1;
    const int xstartx = latset::c<LatSet>(i)[0] < 0 ? Nx - 1 : 0;
    const int xendx = xstartx == 0 ? Nx - 1 : 0;
    const int xdeltax = xstartx == 0 ? 1 : -1;

    for (int z = zstartx; z != zendx; z += zdeltax) {
      for (int y = ystartx; y != yendx; y += ydeltax) {
        for (int x = xstartx; x != xendx; x += xdeltax) {
          std::size_t id = x + y * Nx + z * NxNy;
          std::size_t idn = id + deltaIdx;
          pop[id][i+1] = pop[idn][i+1];
        }
      }
    }
  }
}

template <typename CELL, typename CELLDYNAMICS, typename T, typename LatSet, typename TypePack, typename FieldType>
void Apply(BlockLatticeManager<T,LatSet,TypePack>& LatMan, const BlockFieldManager<FieldType, T, LatSet::d>& BFM) {
  #pragma omp parallel for num_threads(Thread_Num)
  for (std::size_t idx = 0; idx < LatMan.getBlockLats().size(); ++idx) {
    auto& blocklat = LatMan.getBlockLat(idx);
    auto& flagarr = BFM.getBlockField(idx).getField(0);
    CELL cell(0, blocklat);
    for (std::size_t id = 0; id < blocklat.getN(); ++id) {
      cell.setId(id);
      CELLDYNAMICS::Execute(flagarr[id], cell);
    }
  }
}

/*----------------------------------------------
                Simulation Parameters
-----------------------------------------------*/
int Ni;
int Nj;
int Nk;
T Cell_Len;
T RT;
int Thread_Num;
int Block_Num;

// physical properties
T rho_ref;    // g/mm^3
T Kine_Visc;  // mm^2/s kinematic viscosity of the liquid
// init conditions
Vector<T, 3> U_Ini;  // mm/s
T U_Max;

// bcs
Vector<T, 3> U_Wall;  // mm/s

// Simulation settings
int MaxStep;
int OutputStep;
T tol;

void readParam() {
  iniReader param_reader("cavity3d.ini");
  // parallel
  Thread_Num = param_reader.getValue<int>("parallel", "thread_num");
  Block_Num = param_reader.getValue<int>("parallel", "block_num");
  // mesh
  Ni = param_reader.getValue<int>("Mesh", "Ni");
  Nj = param_reader.getValue<int>("Mesh", "Nj");
  Nk = param_reader.getValue<int>("Mesh", "Nk");
  Cell_Len = param_reader.getValue<T>("Mesh", "Cell_Len");
  // physical properties
  rho_ref = param_reader.getValue<T>("Physical_Property", "rho_ref");
  Kine_Visc = param_reader.getValue<T>("Physical_Property", "Kine_Visc");
  // init conditions
  U_Ini[0] = param_reader.getValue<T>("Init_Conditions", "U_Ini0");
  U_Ini[1] = param_reader.getValue<T>("Init_Conditions", "U_Ini1");
  U_Ini[2] = param_reader.getValue<T>("Init_Conditions", "U_Ini2");
  U_Max = param_reader.getValue<T>("Init_Conditions", "U_Max");
  // bcs
  U_Wall[0] = param_reader.getValue<T>("Boundary_Conditions", "Velo_Wall0");
  U_Wall[1] = param_reader.getValue<T>("Boundary_Conditions", "Velo_Wall1");
  U_Wall[2] = param_reader.getValue<T>("Boundary_Conditions", "Velo_Wall2");
  // LB
  RT = param_reader.getValue<T>("LB", "RT");
  // Simulation settings
  MaxStep = param_reader.getValue<int>("Simulation_Settings", "TotalStep");
  OutputStep = param_reader.getValue<int>("Simulation_Settings", "OutputStep");
  tol = param_reader.getValue<T>("tolerance", "tol");
// #ifdef _OPENMP
//   // get max thread number
//   Thread_Num = omp_get_max_threads();
// #endif

//   std::cout << "------------Simulation Parameters:-------------\n" << std::endl;
//   std::cout << "[Simulation_Settings]:" << "TotalStep:         " << MaxStep << "\n"
//             << "OutputStep:        " << OutputStep << "\n"
//             << "Tolerance:         " << tol << "\n"
// #ifdef _OPENMP
//             << "Running on " << Thread_Num << " threads\n"
// #endif
//             << "----------------------------------------------" << std::endl;
}

int main() {
  constexpr std::uint8_t VoidFlag = std::uint8_t(1);
  constexpr std::uint8_t AABBFlag = std::uint8_t(2);
  constexpr std::uint8_t BouncebackFlag = std::uint8_t(4);
  constexpr std::uint8_t BBMovingWallFlag = std::uint8_t(8);

  // Printer::Print_BigBanner(std::string("Initializing..."));

  readParam();

  // converters
  BaseConverter<T> BaseConv(LatSet::cs2);
  BaseConv.ConvertFromRT(Cell_Len, RT, rho_ref, Ni * Cell_Len, U_Max, Kine_Visc);
  UnitConvManager<T> ConvManager(&BaseConv);
  // ConvManager.Check_and_Print();

  // ------------------ define geometry ------------------
  AABB<T, 3> cavity(Vector<T, 3>{},
                    Vector<T, 3>(T(Ni * Cell_Len), T(Nj * Cell_Len), T(Nk * Cell_Len)));
  AABB<T, 3> toplid(
    Vector<T, 3>(Cell_Len, Cell_Len, T((Nk - 1) * Cell_Len)),
    Vector<T, 3>(T((Ni - 1) * Cell_Len), T((Nj - 1) * Cell_Len), T(Nk * Cell_Len)));
  BlockGeometry3D<T> Geo(Ni, Nj, Nk, Thread_Num, cavity, Cell_Len);

  // ------------------ define flag field ------------------
  BlockFieldManager<FLAG, T, 3> FlagFM(Geo, VoidFlag);
  FlagFM.forEach(cavity,
                 [&](FLAG& field, std::size_t id) { field.SetField(id, AABBFlag); });
  FlagFM.template SetupBoundary<LatSet>(cavity, BouncebackFlag);
  FlagFM.forEach(toplid, [&](FLAG& field, std::size_t id) {
    if (util::isFlag(field.get(id), BouncebackFlag)) field.SetField(id, BBMovingWallFlag);
  });

  Vector<T, 3> LatU_Wall = BaseConv.getLatticeU(U_Wall);

  // ------------------ define lattice ------------------
  // SOA
  // using FIELDSSOA = TypePack<RHO<T>, VELOCITY<T, LatSet::d>, NPOPSOA<T, LatSet::q>>;
  // using CELLSOA = NCellSOA<T, LatSet, FIELDSSOA>;
  // ValuePack InitValues(BaseConv.getLatRhoInit(), Vector<T, 3>{}, T{});
  // BlockLatticeManager<T, LatSet, FIELDSSOA> NSLatticeSOA(Geo, InitValues, BaseConv);
  // NSLatticeSOA.getField<VELOCITY<T, LatSet::d>>().forEach(
  //   toplid, FlagFM, BBMovingWallFlag,
  //   [&](auto& field, std::size_t id) { field.SetField(id, LatU_Wall); });
  // using BulkTaskSOA = tmp::Key_TypePair<AABBFlag, collision::BGK<moment::rhoU<CELLSOA>, equilibrium::SecondOrder<CELLSOA>>>;
  // using NSTaskSOA = TaskSelector<std::uint8_t, CELLSOA, BulkTaskSOA>;

  // AOS
  // using FIELDSAOS = TypePack<RHO<T>, VELOCITY<T, LatSet::d>, NPOPAOS<T, LatSet::q>>;
  // using CELLAOS = NCellAOS<T, LatSet, FIELDSAOS>;
  // ValuePack InitValues(BaseConv.getLatRhoInit(), Vector<T, 3>{}, Vector<T, LatSet::q>{});
  // BlockLatticeManager<T, LatSet, FIELDSAOS> NSLatticeAOS(Geo, InitValues, BaseConv);
  // NSLatticeAOS.getField<VELOCITY<T, LatSet::d>>().forEach(
  //   toplid, FlagFM, BBMovingWallFlag,
  //   [&](auto& field, std::size_t id) { field.SetField(id, LatU_Wall); });
  // using BulkTaskAOS = tmp::Key_TypePair<AABBFlag, collision::BGK<moment::rhoU<CELLAOS>, equilibrium::SecondOrder<CELLAOS>>>;
  // using NSTaskAOS = TaskSelector<std::uint8_t, CELLAOS, BulkTaskAOS>;

  // cyclic
  // using FIELDS = TypePack<RHO<T>, VELOCITY<T, LatSet::d>, POP<T, LatSet::q>>;
  // using CELL = Cell<T, LatSet, FIELDS>;
  // ValuePack InitValues(BaseConv.getLatRhoInit(), Vector<T, 3>{}, T{});
  // BlockLatticeManager<T, LatSet, FIELDS> NSLattice(Geo, InitValues, BaseConv);
  // NSLattice.getField<VELOCITY<T, LatSet::d>>().forEach(
  //   toplid, FlagFM, BBMovingWallFlag,
  //   [&](auto& field, std::size_t id) { field.SetField(id, LatU_Wall); });
  // using BulkTask = tmp::Key_TypePair<AABBFlag, collision::BGK<moment::rhoU<CELL>, equilibrium::SecondOrder<CELL>>>;
  // using NSTask = TaskSelector<std::uint8_t, CELL, BulkTask>;


  // Printer::Print_BigBanner(std::string("Start Calculation..."));
  std::cout << "Total Cells: " << Geo.getTotalCellNum() << std::endl;

  // count and timer
  Timer MainLoopTimer;



  // for(int i = 0; i < 10; ++i){
  //   Apply<CELLSOA,NSTaskSOA>(NSLatticeSOA, FlagFM);
  //   NStreamSOA(NSLatticeSOA);
  // }
  // MainLoopTimer.START_TIMER();
  // while (MainLoopTimer() < MaxStep) {
  //   Apply<CELLSOA,NSTaskSOA>(NSLatticeSOA, FlagFM);
  //   NStreamSOA(NSLatticeSOA);
  //   ++MainLoopTimer;
  // }
  // MainLoopTimer.END_TIMER();
  // MainLoopTimer.Print_MainLoopPerformance(Geo.getTotalCellNum());
  // Printer::Endl();

  // for(int i = 0; i < 10; ++i){
  //   Apply<CELLAOS,NSTaskAOS>(NSLatticeAOS, FlagFM);
  //   NStreamAOS(NSLatticeAOS);
  // }
  // MainLoopTimer.START_TIMER();
  // while (MainLoopTimer() < MaxStep) {
  //   Apply<CELLAOS,NSTaskAOS>(NSLatticeAOS, FlagFM);
  //   NStreamAOS(NSLatticeAOS);
  //   ++MainLoopTimer;
  // }
  // MainLoopTimer.END_TIMER();
  // MainLoopTimer.Print_MainLoopPerformance(Geo.getTotalCellNum());
  // Printer::Endl();

  // for(int i = 0; i < 10; ++i){
  //   NSLattice.ApplyCellDynamics<NSTask>(FlagFM);
  //   NSLattice.Stream();
  // }
  // MainLoopTimer.START_TIMER();
  // while (MainLoopTimer() < MaxStep) {
  //   NSLattice.ApplyCellDynamics<NSTask>(FlagFM);
  //   NSLattice.Stream();
  //   ++MainLoopTimer;
  // }
  // MainLoopTimer.END_TIMER();
  // MainLoopTimer.Print_MainLoopPerformance(Geo.getTotalCellNum());
  // Printer::Endl();

  return 0;
}
