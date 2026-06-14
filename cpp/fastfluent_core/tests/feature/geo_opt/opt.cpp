/* This file is part of FreeLB
 *
 *
 */

#include "freelb.h"
#include "freelb.hh"

using T = FLOAT;
using LatSet = D3Q19<T>;

/*----------------------------------------------
                Simulation Parameters
-----------------------------------------------*/
T Cell_Len;
int minBlockCell_Len;
int maxBlockCell_Len;
int Thread_Num;

// Geometry
T CentreX;
T CentreY;
T CentreZ;

void readParam() {
  iniReader param_reader("param.ini");
  // parallel
  Thread_Num = param_reader.getValue<int>("parallel", "thread_num");

  Cell_Len = param_reader.getValue<T>("Mesh", "Cell_Len");
  minBlockCell_Len = param_reader.getValue<int>("Mesh", "minBlockCell_Len");
  maxBlockCell_Len = param_reader.getValue<int>("Mesh", "maxBlockCell_Len");
  // geometry
  CentreX = param_reader.getValue<T>("Geometry", "CentreX");
  CentreY = param_reader.getValue<T>("Geometry", "CentreY");
  CentreZ = param_reader.getValue<T>("Geometry", "CentreZ");
}

int main(int argc, char* argv[]) {
  constexpr std::uint8_t VoidFlag = std::uint8_t(1);
  constexpr std::uint8_t AABBFlag = std::uint8_t(2);
  constexpr std::uint8_t BouncebackFlag = std::uint8_t(4);
  // constexpr std::uint8_t InletFlag = std::uint8_t(8);

  mpi().init(&argc, &argv);

  MPI_DEBUG_WAIT

  Printer::Print_BigBanner(std::string("Initializing..."));

  readParam();

  // define geometry, y is the vertical direction
  StlReader<T> reader("./core_x_t_R.stl", Cell_Len, 1.);
  BlockGeometryHelper3D<T> GeoHelper(reader, maxBlockCell_Len, 2, 1, false);
  GeoHelper.getFlagField().Init(reader, 1, AABBFlag, VoidFlag);
  GeoHelper.getFlagField().template SetupBoundary<LatSet>(VoidFlag, AABBFlag, AABBFlag);
  // GeoHelper.Init(maxBlockCell_Len);
  // GeoHelper.CreateBlocks(true);
  // GeoHelper.RemoveUnusedCells();
  // // GeoHelper.AdaptiveOptimization(mpi().getSize(), mpi().getSize(), true);
  // // GeoHelper.Optimize(mpi().getSize(), true, true);
  // GeoHelper.Optimize(Thread_Num, true, true);
  // GeoHelper.RemoveUnusedCells();
  // GeoHelper.LoadOptimization();
  // GeoHelper.IterateAndOptimize(Thread_Num, minBlockCell_Len, maxBlockCell_Len, false);
  GeoHelper.RCBOptimization(Thread_Num, true);
  GeoHelper.LoadBalancing(mpi().getSize());
  // GeoHelper.LoadBalancing(Thread_Num);
  BlockGeometry3D<T> Geo(GeoHelper);

  // 0 30 30
  Cylinder<T> Inlet(T(11), Vector<T, 3>{Cell_Len, T{}, T{}}, Vector<T, 3>{CentreX, CentreY, CentreZ});
  // ------------------ define flag field ------------------
  BlockFieldManager<FLAG, T, LatSet::d> FlagFM(Geo, VoidFlag);
  FlagFM.ReadOctree(reader.getTree(), AABBFlag);
  FlagFM.CleanLonelyFlags<LatSet>(AABBFlag, VoidFlag, 1, true);
  // we change the position of AABBFlag, VoidFlag here to create bdflag from voidflag not aabbflag
  FlagFM.template SetupBoundary<LatSet>(VoidFlag, AABBFlag, BouncebackFlag);
  // FlagFM.forEach(Inlet, [&](FLAG& field, std::size_t id) {
  //   if (util::isFlag(field.get(id), BouncebackFlag)) field.SetField(id, InletFlag);
  // });

  FieldStatistics FlagStat(FlagFM);
  FlagStat.printFlagStatistics();

  vtmo::ScalarWriter Flagvtm("Flag", FlagFM);
  vtmo::vtmWriter<T, LatSet::d> FlagWriter("GeoFlag", Geo, 1);
  FlagWriter.addWriterSet(Flagvtm);
  FlagWriter.WriteBinary();

  return 0;
}
