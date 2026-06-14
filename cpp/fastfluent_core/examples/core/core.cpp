/* This file is part of FreeLB
 *
 *
 */

#include "freelb.h"
#include "freelb.hh"
#include "lbm/freeSurface.h"
#include "offLattice/marchingCube.hh"

using T = FLOAT;
using LatSet = D3Q19<T>;

/*----------------------------------------------
                Simulation Parameters
-----------------------------------------------*/
T Cell_Len;
int minBlockCell_Len;
int maxBlockCell_Len;
T RT;
T deltaT;
int Thread_Num;

// Geometry
T CentreX;
T CentreY;
T CentreZ;

// physical properties
T rho_ref;    // g/mm^3
T Kine_Visc;  // mm^2/s kinematic viscosity of the liquid
/*free surface*/
// surface tension: N/m = kg/s^2
// fluid: 0.0728 N/m at 20 C = 0.0728 kg/s^2 = 72.8 g/s^2
T surface_tension_coefficient;
// Anti jitter value
T VOF_Trans_Threshold;
// When to remove lonely cells
T LonelyThreshold;
// init conditions
Vector<T, LatSet::d> U_Ini;  // mm/s
T U_Max;

// bcs
Vector<T, LatSet::d> U_Wall;  // mm/s

// rheology
// this could be evaluated at compile time but we need to convert to lattice unit
T _E1_minShearRate;
T _E1_maxShearRate;
T _E2_minShearRate;
T _E2_maxShearRate;
// hers-cross model
// this could be evaluated at compile time but we need to convert to lattice unit
T _cross_eta0; // visc: mm^2/s
T _cross_t; // time: s
T _cross_m; // 1
T _hers_k; // visc: mm^2/s
T _hers_m; // 1
// constexpr T _hers_k = 35356.;
// constexpr T _hers_m = -1.02161;
// constexpr T _cross_eta0 = 10000.;
// constexpr T _cross_t = 0.02183;
// constexpr T _cross_m = 1.457;

// LES
T Smagorinsky;

// Simulation settings
int MaxStep;
int OutputStep;
int WriteStep;

void readParam() {
  iniReader param_reader("core.ini");
  // parallel
  Thread_Num = param_reader.getValue<int>("parallel", "thread_num");

  Cell_Len = param_reader.getValue<T>("Mesh", "Cell_Len");
  minBlockCell_Len = param_reader.getValue<int>("Mesh", "minBlockCell_Len");
  maxBlockCell_Len = param_reader.getValue<int>("Mesh", "maxBlockCell_Len");
  // geometry
  CentreX = param_reader.getValue<T>("Geometry", "CentreX");
  CentreY = param_reader.getValue<T>("Geometry", "CentreY");
  CentreZ = param_reader.getValue<T>("Geometry", "CentreZ");

  // physical properties
  rho_ref = param_reader.getValue<T>("Physical_Property", "rho_ref");
  Kine_Visc = param_reader.getValue<T>("Physical_Property", "Kine_Visc");

  // Rheology
  _E1_minShearRate = param_reader.getValue<T>("Rheology", "E1_minShearRate");
  _E1_maxShearRate = param_reader.getValue<T>("Rheology", "E1_maxShearRate");
  _E2_minShearRate = param_reader.getValue<T>("Rheology", "E2_minShearRate");
  _E2_maxShearRate = param_reader.getValue<T>("Rheology", "E2_maxShearRate");
  _cross_eta0 = param_reader.getValue<T>("Rheology", "cross_eta0");
  _cross_t = param_reader.getValue<T>("Rheology", "cross_t");
  _cross_m = param_reader.getValue<T>("Rheology", "cross_m");
  _hers_k = param_reader.getValue<T>("Rheology", "hers_k");
  _hers_m = param_reader.getValue<T>("Rheology", "hers_m");

  /*free surface*/
  surface_tension_coefficient =
    param_reader.getValue<T>("Free_Surface", "surface_tension_coefficient");
  VOF_Trans_Threshold = param_reader.getValue<T>("Free_Surface", "VOF_Trans_Threshold");
  LonelyThreshold = param_reader.getValue<T>("Free_Surface", "LonelyThreshold");

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
  deltaT = param_reader.getValue<T>("LB", "deltaT");
  // LES
  Smagorinsky = param_reader.getValue<T>("LES", "Smagorinsky");
  // Simulation settings
  MaxStep = param_reader.getValue<int>("Simulation_Settings", "TotalStep");
  OutputStep = param_reader.getValue<int>("Simulation_Settings", "OutputStep");
  WriteStep = param_reader.getValue<int>("Simulation_Settings", "WriteStep");

  MPI_RANK(0)
  std::cout << "------------Simulation Parameters:-------------\n" << std::endl;
  std::cout << "[Simulation_Settings]:" << "TotalStep:         " << MaxStep << "\n"
            << "OutputStep:        " << OutputStep << "\n"
#ifdef _OPENMP
            << "Running on " << Thread_Num << " threads\n"
#endif
            << "----------------------------------------------" << std::endl;
}

namespace ceramicRheology {

// define field
struct E1_minShearRateBase : public FieldBase<1> {};
struct E1_maxShearRateBase : public FieldBase<1> {};
struct E2_minShearRateBase : public FieldBase<1> {};
struct E2_maxShearRateBase : public FieldBase<1> {};
struct Cross_eta0Base : public FieldBase<1> {};
struct Cross_tBase : public FieldBase<1> {};
struct Cross_mBase : public FieldBase<1> {};
struct Hers_kBase : public FieldBase<1> {};
struct Hers_mBase : public FieldBase<1> {};

template <typename T>
using E1_minShearRate = Data<T, E1_minShearRateBase>;
template <typename T>
using E1_maxShearRate = Data<T, E1_maxShearRateBase>;
template <typename T>
using E2_minShearRate = Data<T, E2_minShearRateBase>;
template <typename T>
using E2_maxShearRate = Data<T, E2_maxShearRateBase>;
template <typename T>
using Cross_eta0 = Data<T, Cross_eta0Base>;
template <typename T>
using Cross_t = Data<T, Cross_tBase>;
template <typename T>
using Cross_m = Data<T, Cross_mBase>;
template <typename T>
using Hers_k = Data<T, Hers_kBase>;
template <typename T>
using Hers_m = Data<T, Hers_mBase>;

// collection
template <typename T>
using AllRheologyPARAMS = TypePack<E1_minShearRate<T>, E1_maxShearRate<T>, E2_minShearRate<T>, E2_maxShearRate<T>,
Cross_eta0<T>, Cross_t<T>, Cross_m<T>, Hers_k<T>, Hers_m<T>>;
template <typename T>
using AllShearRatePARAMS = TypePack<E1_minShearRate<T>, E1_maxShearRate<T>, E2_minShearRate<T>, E2_maxShearRate<T>>;

// compute omega from magnitude of shear rate
template <typename CELLTYPE>
struct core_Omega {
  using CELL = CELLTYPE;
  using T = typename CELL::FloatType;
  using LatSet = typename CELL::LatticeSet;
  // gamma is in lattice unit
  static inline T get(T gamma, CELL& cell) {
    // all parameters are in lattice unit
    T nu{};
    const T gamma1_min = cell.template get<E1_minShearRate<T>>();
    const T gamma2_max = cell.template get<E2_maxShearRate<T>>();
    const T gamma1_max = cell.template get<E1_maxShearRate<T>>();

    const T cross_eta0 = cell.template get<Cross_eta0<T>>();
    const T cross_t = cell.template get<Cross_t<T>>();
    const T cross_m = cell.template get<Cross_m<T>>();
    const T hers_k = cell.template get<Hers_k<T>>();
    const T hers_m = cell.template get<Hers_m<T>>();

    // for stable reason
    if (gamma < gamma1_min) gamma = gamma1_min;
    if (gamma > gamma2_max) gamma = gamma2_max;
    if (gamma < gamma1_max) {
      // scheme 1: hershel-cross
      nu = cross_eta0/(1+std::pow(cross_t*gamma, cross_m)) + hers_k*std::pow(gamma, hers_m);
    } else {
      // scheme 2: cross
      nu = cross_eta0/(1+std::pow(cross_t*gamma, cross_m));
    }
    // lat_nu = cs^2 * (tau - 0.5) = (1/omega - 0.5)/3
    T omega = T{1} / (nu * LatSet::InvCs2 + T{0.5});
    return omega;
  }
};

} // namespace ceramicRheology

namespace collision {

template <typename MomentaScheme, typename EquilibriumScheme, typename ForceScheme, typename RheologyOemga>
struct coreRheology_BGKForce {
  using CELL = typename EquilibriumScheme::CELLTYPE;
  using T = typename CELL::FloatType;
  using LatSet = typename CELL::LatticeSet;
  using equilibriumscheme = EquilibriumScheme;
  using GenericRho = typename CELL::GenericRho;

  static void apply(CELL& cell) {
    // update macroscopic variables
    T rho{};
    Vector<T, LatSet::d> u{};
    const auto force = ForceScheme::getForce(cell);
    MomentaScheme::apply(cell, force, rho, u);
    // strain rate
    std::array<T, util::SymmetricMatrixSize<LatSet::d>()> strain_rate{};
    moment::template strainRate<CELL>::apply(cell, rho, u, strain_rate);
    // magnitude of shear rate
    T gamma = moment::template shearRateMag<CELL>::get(strain_rate);
    // compute force term
    std::array<T, LatSet::q> fi{};
    ForceScheme::apply(u, force, fi);
    // equilibrium distribution function
    std::array<T, LatSet::q> feq{};
    EquilibriumScheme::apply(feq, rho, u);
    // Rheology omega
    const T omega = RheologyOemga::get(gamma, cell);
    const T _omega = T{1} - omega;
    const T fomega = T{1} - T{0.5} * omega;

    for (unsigned int i = 0; i < LatSet::q; ++i) {
      cell[i] = omega * feq[i] + _omega * cell[i] + fomega * fi[i];
    }
  }
};

} //namespace collision

int main(int argc, char* argv[]) {
  constexpr std::uint8_t VoidFlag = std::uint8_t(1);
  constexpr std::uint8_t AABBFlag = std::uint8_t(2);
  constexpr std::uint8_t BouncebackFlag = std::uint8_t(4);
  constexpr std::uint8_t InletFlag = std::uint8_t(8);

  mpi().init(&argc, &argv);

  MPI_DEBUG_WAIT

  Printer::Print_BigBanner(std::string("Initializing..."));

  readParam();

  // converters
  BaseConverter<T> BaseConv(LatSet::cs2);
  // BaseConv.ConvertFromRT(Cell_Len, RT, rho_ref, T(200), U_Max, Kine_Visc);
  BaseConv.ConvertFromTimeStep(Cell_Len, deltaT, rho_ref, T(270), U_Max, Kine_Visc);
  IF_MPI_RANK(0){
    T numax = _cross_eta0/(1+std::pow(_cross_t*_E1_minShearRate, _cross_m)) + _hers_k*std::pow(_E1_minShearRate, _hers_m);
    T numin = _cross_eta0/(1+std::pow(_cross_t*_E2_maxShearRate, _cross_m));
    T maxRT = T(0.5) + deltaT * numax / (LatSet::cs2 * Cell_Len * Cell_Len);
    T minRT = T(0.5) + deltaT * numin / (LatSet::cs2 * Cell_Len * Cell_Len);
    std::cout << "minRT: " << minRT << ", maxRT: " << maxRT <<std::endl;
  }
  UnitConvManager<T> ConvManager(&BaseConv);
  ConvManager.Check_and_Print();

  // define geometry, y is the vertical direction
  StlReader<T> reader("./core_x_t_R.stl", Cell_Len, 1.);
  BlockGeometryHelper3D<T> GeoHelper(reader, maxBlockCell_Len, 2, 1, false);
  GeoHelper.getFlagField().Init(reader, 1, AABBFlag, VoidFlag);
  GeoHelper.getFlagField().template SetupBoundary<LatSet>(VoidFlag, AABBFlag, AABBFlag);
  // GeoHelper.CreateBlocks(true);
  // GeoHelper.RemoveUnusedCells();
  // GeoHelper.AdaptiveOptimization(mpi().getSize(), mpi().getSize(), true);
  // GeoHelper.Optimize(mpi().getSize(), true, true);
  // GeoHelper.RemoveUnusedCells();
  // GeoHelper.IterateAndOptimize(Thread_Num, minBlockCell_Len, maxBlockCell_Len, false);
  GeoHelper.RCBOptimization(mpi().getSize());
  GeoHelper.LoadBalancing(mpi().getSize());
  BlockGeometry3D<T> Geo(GeoHelper);

  // 460.274, 0, 324.5   cellsize = 0.2 bd from aabbflag
  // 459.974, 0, 324.5   cellsize = 0.4, bd from voidflag
  // after rotate:
  // 0 30 30
  // Cylinder<T> Inlet(T(10), Vector<T, 3>{Cell_Len, T{}, T{}}, Vector<T, 3>{T{459.974}, T{0},T{324.5}});
  Cylinder<T> Inlet(T(11), Vector<T, 3>{Cell_Len, T{}, T{}}, Vector<T, 3>{CentreX, CentreY, CentreZ});
  // ------------------ define flag field ------------------
  BlockFieldManager<FLAG, T, LatSet::d> FlagFM(Geo, VoidFlag);
  FlagFM.ReadOctree(reader.getTree(), AABBFlag);
  FlagFM.CleanLonelyFlags<LatSet>(AABBFlag, VoidFlag, 1, true);
  // we change the position of AABBFlag, VoidFlag here to create bdflag from voidflag not aabbflag
  FlagFM.template SetupBoundary<LatSet>(VoidFlag, AABBFlag, BouncebackFlag);
  FlagFM.forEach(Inlet, [&](FLAG& field, std::size_t id) {
    if (util::isFlag(field.get(id), BouncebackFlag)) field.SetField(id, InletFlag);
  });

  FieldStatistics FlagStat(FlagFM);
  FlagStat.printFlagStatistics();

  vtmo::ScalarWriter Flagvtm("Flag", FlagFM);
  vtmo::vtmWriter<T, LatSet::d> FlagWriter("GeoFlag", Geo, 1);
  FlagWriter.addWriterSet(Flagvtm);
  FlagWriter.WriteBinary();

  // ------------------ define lattice ------------------
  Vector<T, LatSet::d> LatU_Wall = BaseConv.getLatticeU(U_Wall);
  using NSFIELDS = TypePack<RHO<T>, VELOCITY<T, LatSet::d>, POP<T, LatSet::q>, SCALARCONSTFORCE<T>, CONSTU<T, LatSet::d>, StrainRateMag<T>>;
  using NSRHEOFIELDS = MergeFieldPack<NSFIELDS, ceramicRheology::AllRheologyPARAMS<T>>::mergedpack;
  using ALLFIELDS = MergeFieldPack<NSRHEOFIELDS, olbfs::FSFIELDS<T, LatSet>, olbfs::FSPARAMS<T>>::mergedpack;

  // a conversion factor of unit s^2 / g
  // [surface_tension_coefficient_factor * surface_tension_coefficient] = [1]
  // (LatRT_ - T(0.5)) * cs2 * deltaX_ * deltaX_ / VisKine_

  T surface_tension_coefficient_factor =
    BaseConv.Conv_Time * BaseConv.Conv_Time / (rho_ref * std::pow(BaseConv.Conv_L, 3));
  // gravity: -y direction
  ValuePack NSInitValues(BaseConv.getLatRhoInit(), Vector<T, LatSet::d>{}, T{},
                         -BaseConv.Lattice_g, LatU_Wall, T{}); //-BaseConv.Lattice_g
  ValuePack RheoInitValues(BaseConv.getLatStrainRate(_E1_minShearRate), BaseConv.getLatStrainRate(_E1_maxShearRate),
    BaseConv.getLatStrainRate(_E2_minShearRate), BaseConv.getLatStrainRate(_E2_maxShearRate),
    BaseConv.getLatVisKine(_cross_eta0), BaseConv.getLatTime(_cross_t), _cross_m,
    BaseConv.getLatVisKine(_hers_k), _hers_m);
  auto NSRheoInit = mergeValuePack(NSInitValues, RheoInitValues);
  ValuePack FSInitValues(olbfs::FSType::Void, olbfs::FSFlag::None, T{}, T{}, Vector<T, LatSet::q>{}, Vector<T, 3>{});
  ValuePack FSParamsInitValues(
    LonelyThreshold, VOF_Trans_Threshold, true,
    surface_tension_coefficient_factor * surface_tension_coefficient);

  auto ALLValues = mergeValuePack(NSRheoInit, FSInitValues, FSParamsInitValues);

  using NSCELL = Cell<T, LatSet, ALLFIELDS>;
  using NSLAT = BlockLatticeManager<T, LatSet, ALLFIELDS>;
  using NSBlockLat = BlockLattice<T, LatSet, ALLFIELDS>;
  using NSBlockLatMan = BlockLatticeManager<T, LatSet, ALLFIELDS>;
  BlockLatticeManager<T, LatSet, ALLFIELDS> NSLattice(Geo, ALLValues, BaseConv);

  FieldStatistics RhoStat(NSLattice.getField<RHO<T>>());
  FieldStatistics MassStat(NSLattice.getField<olbfs::MASS<T>>());
  FieldStatistics StateStat(NSLattice.getField<olbfs::STATE>());
  FieldStatistics ShearRateStat(NSLattice.getField<StrainRateMag<T>>());

  // set initial value of field
  NSLattice.getField<VELOCITY<T, LatSet::d>>().forEach(
    FlagFM, InletFlag,
    [&](auto& field, std::size_t id) { field.SetField(id, LatU_Wall); });

  //// free surface
  // set cell state
  NSLattice.getField<olbfs::STATE>().forEach(
    FlagFM, AABBFlag,
    [&](auto& field, std::size_t id) { field.SetField(id, olbfs::FSType::Gas); });

  NSLattice.getField<olbfs::STATE>().forEach(
    FlagFM, InletFlag,
    [&](auto& field, std::size_t id) { field.SetField(id, olbfs::FSType::Fluid); });
  NSLattice.getField<olbfs::STATE>().forEach(
    FlagFM, BouncebackFlag,
    [&](auto& field, std::size_t id) { field.SetField(id, olbfs::FSType::Wall); });
  olbfs::FreeSurfaceHelper<NSLAT>::Init(NSLattice);

  std::size_t max_FluidCellNum = StateStat.getFlagCount(static_cast<olbfs::FSType>(olbfs::FSType::Gas | olbfs::FSType::Interface | olbfs::FSType::Fluid));

  StateStat.printFlagStatistics();


  //// end free surface

  // define task/ dynamics:
  // using NSBulkTask = tmp::Key_TypePair<olbfs::FSType::Fluid | olbfs::FSType::Interface,
  //   collision::BGKForce<moment::forcerhoU<NSCELL, force::ScalarConstForce<NSCELL, 1>, true, 1>,
  //   equilibrium::SecondOrder<NSCELL>, force::ScalarConstForce<NSCELL, 1>>>;
  using NSBulkTask = tmp::Key_TypePair<olbfs::FSType::Fluid | olbfs::FSType::Interface,
    collision::coreRheology_BGKForce<moment::forcerhoU<NSCELL, force::ScalarConstForce<NSCELL, 1>, true, 1>,
    equilibrium::SecondOrder<NSCELL>, force::ScalarConstForce<NSCELL, 1>, ceramicRheology::core_Omega<NSCELL>>>;
  using NSWallTask = tmp::Key_TypePair<olbfs::FSType::Wall, collision::BounceBack<NSCELL>>;

  using NSTaskSelector = TaskSelector<std::uint8_t, NSCELL, NSBulkTask, NSWallTask>;

  // inlet u task
  using InletTask = tmp::Key_TypePair<InletFlag, moment::constU<NSCELL, true>>;
  using InletTaskSelector = TaskSelector<std::uint8_t, NSCELL, InletTask>;

  // get shear rate
  using shearRateTask = tmp::Key_TypePair<AABBFlag, moment::shearRateMag<NSCELL, true>>;
  using shearRateTaskSelector = TaskSelector<std::uint8_t, NSCELL, shearRateTask>;

  // bcs
  BBLikeFixedBlockBdManager<bounceback::normal<NSCELL>,
                            BlockLatticeManager<T, LatSet, ALLFIELDS>,
                            BlockFieldManager<FLAG, T, LatSet::d>>
    NS_BB("NS_BB", NSLattice, FlagFM, BouncebackFlag, VoidFlag);
  BBLikeFixedBlockBdManager<bounceback::movingwall<NSCELL>,
                            BlockLatticeManager<T, LatSet, ALLFIELDS>,
                            BlockFieldManager<FLAG, T, LatSet::d>>
    NS_Inlet("NS_BBMW", NSLattice, FlagFM, InletFlag, VoidFlag);

  // vtmo::ScalarWriter rhovtm("rho", NSLattice.getField<RHO<T>>());
  // vtmo::ScalarWriter MassWriter("Mass", NSLattice.getField<olbfs::MASS<T>>());
  // vtmo::VectorWriter VeloWriter("Velo", NSLattice.getField<VELOCITY<T, LatSet::d>>());
  // vtmo::ScalarWriter VOFWriter("VOF", NSLattice.getField<olbfs::VOLUMEFRAC<T>>());
  // vtmo::ScalarWriter StateWriter("State", NSLattice.getField<olbfs::STATE>());
  vtmo::PhysScalarWriter<StrainRateMag<T>, LatSet::d, float> PhysShearRateWriter("ShearRate", NSLattice.getField<StrainRateMag<T>>(),
    std::bind(&BaseConverter<T>::getPhysStrainRate, &BaseConv, std::placeholders::_1));
  vtmo::PhysVectorWriter<VELOCITY<T, LatSet::d>, LatSet::d, float> physVecWriter("physVelocity",NSLattice.getField<VELOCITY<T, LatSet::d>>(),
    std::bind(&BaseConverter<T>::getPhysU<LatSet::d>, &BaseConv, std::placeholders::_1));
  vtmo::vtmWriter<T, LatSet::d> Writer("core", Geo, 1);
  Writer.addWriterSet(PhysShearRateWriter, physVecWriter);

  // count and timer
  Timer MainLoopTimer;
  Timer OutputTimer;

  Writer.WriteBinary(MainLoopTimer());
  // write freeSurface stl
  // set wall vof to 0
  NSLattice.getField<olbfs::VOLUMEFRAC<T>>().forEach(
    NSLattice.getField<olbfs::STATE>(), olbfs::FSType::Wall,
    [&](auto& field, std::size_t id) { field.SetField(id, T{}); });
  // mc algorithm
  offlat::MarchingCubeSurface<T, olbfs::VOLUMEFRAC<T>> mc(NSLattice.getField<olbfs::VOLUMEFRAC<T>>(), T{0.5});
  offlat::TriangleSet<T> triangles;
  mc.generateIsoSurface(triangles);
  triangles.writeBinarySTL("SurfacemarchingCube" + std::to_string(MainLoopTimer()));
  // set wall vof back to 1
  NSLattice.getField<olbfs::VOLUMEFRAC<T>>().forEach(
    NSLattice.getField<olbfs::STATE>(), olbfs::FSType::Wall,
    [&](auto& field, std::size_t id) { field.SetField(id, T{1}); });

  // write vtu
  vtuSurface::physScalarWriter<StrainRateMag<T>, T, float> vtuStrainRateWriter("ShearRate", NSLattice.getField<StrainRateMag<T>>(), triangles,
    std::bind(&BaseConverter<T>::getPhysStrainRate, &BaseConv, std::placeholders::_1));
  vtuSurface::physVectorWriter<VELOCITY<T, LatSet::d>, T, float> vtuVeloWriter("physVelocity", NSLattice.getField<VELOCITY<T, LatSet::d>>(), triangles,
    std::bind(&BaseConverter<T>::getPhysU<LatSet::d>, &BaseConv, std::placeholders::_1));
  vtuSurface::vtuManager<T> vtuWriter("corevtu", triangles);
  vtuWriter.addWriter(vtuStrainRateWriter, vtuVeloWriter);

  vtuWriter.WriteBinary(MainLoopTimer());

  Printer::Print_BigBanner(std::string("Start Calculation..."));
  T fillLevel{};

  while (MainLoopTimer() < MaxStep && fillLevel < T{1}) {
    ++MainLoopTimer;
    ++OutputTimer;

    NSLattice.ApplyCellDynamics<NSTaskSelector>(NSLattice.getField<olbfs::STATE>());
    NSLattice.ApplyCellDynamics<InletTaskSelector>(FlagFM);
    NSLattice.Stream();
    NS_Inlet.Apply();
    NSLattice.NormalAllCommunicate();

    olbfs::FreeSurfaceApply<NSBlockLatMan>::Apply(NSLattice);

    if (MainLoopTimer() % OutputStep == 0) {
      OutputTimer.Print_InnerLoopPerformance(Geo.getTotalCellNum(), OutputStep);
      // shear rate
      NSLattice.ApplyCellDynamics<shearRateTaskSelector>(FlagFM);

      fillLevel = T(StateStat.getFlagCount(olbfs::FSType::Fluid))/T(max_FluidCellNum);
      Printer::Print("Fill Level(%)", fillLevel * 100);
      Printer::Print("Average Rho", RhoStat.getAverage());
      // Printer::Print("Average Mass", MassStat.getAverage());
      Printer::Print("Max Mass", MassStat.getMax());
      Printer::Print("Min Mass", MassStat.getMin());
      Printer::Print("Max ShearRate", BaseConv.getPhysStrainRate(ShearRateStat.getMax()));
      Printer::Endl();
    }

    if (MainLoopTimer() % WriteStep == 0) {

      Writer.WriteBinary(MainLoopTimer());

      // write freeSurface stl
      // set wall vof to 0
      NSLattice.getField<olbfs::VOLUMEFRAC<T>>().forEach(
        NSLattice.getField<olbfs::STATE>(), olbfs::FSType::Wall,
        [&](auto& field, std::size_t id) { field.SetField(id, T{}); });
      // re-generate iso surface
      mc.generateIsoSurface(triangles);
      triangles.writeBinarySTL("SurfacemarchingCube" + std::to_string(MainLoopTimer()));
      // set wall vof back to 1
      NSLattice.getField<olbfs::VOLUMEFRAC<T>>().forEach(
        NSLattice.getField<olbfs::STATE>(), olbfs::FSType::Wall,
        [&](auto& field, std::size_t id) { field.SetField(id, T{1}); });

      vtuWriter.WriteBinary(MainLoopTimer());
    }

  }

  Writer.WriteBinary(MainLoopTimer());
  // write freeSurface stl
  // set wall vof to 0
  NSLattice.getField<olbfs::VOLUMEFRAC<T>>().forEach(
    NSLattice.getField<olbfs::STATE>(), olbfs::FSType::Wall,
    [&](auto& field, std::size_t id) { field.SetField(id, T{}); });
  // re-generate iso surface
  mc.generateIsoSurface(triangles);
  triangles.writeBinarySTL("SurfacemarchingCube" + std::to_string(MainLoopTimer()));
  vtuWriter.WriteBinary(MainLoopTimer());

  Printer::Print_BigBanner(std::string("Calculation Complete!"));
  MainLoopTimer.Print_MainLoopPerformance(Geo.getTotalCellNum());
  Printer::Print("Total PhysTime", BaseConv.getPhysTime(MainLoopTimer()));
  Printer::Endl();

  return 0;
}
