# The benchmarking method

How a performance number in this lab is measured, so that two numbers from
two reports are comparable.

## What is measured

The unit of work in this lab is a **decision**: one full pass of a stimulus
through the network to an output readout, at a fixed tick. For a
connectome-scale LIF network the measured quantities are:

| Quantity | Definition |
|----------|-----------|
| `ms/step` | wall time of one integration step (one tick of network time) over the whole network, after warm-up, median of the run |
| `ms/decision` | wall time of one decision at the target tick rate (may span several integration steps if the network's natural time constant is coarser than the decision period) |
| `decision/s` | reciprocal of the above at the tick rate the application actually needs (this is the number an agent loop cares about) |
| `peak RAM` | maximum resident memory of the simulation process, including loaded circuit |
| `power` | optional; wall draw of the box while the run is the dominant load |

## Protocol

1. **Circuit and code are named, versions pinned.** A row in the results
   table names the circuit (file + hash), the backend (simulator + version
   + precision), and the experiment commit that produced it.
2. **Warm-up, then median.** The first steps warm caches and allocators;
   discard them. Report the **median** of the measured steps, with the
   10th–90th percentile range when the distribution is not tight.
3. **The grid is declared before the run.** Duration (network time
   simulated) and repeat count form a grid; the grid, not ad-hoc reruns,
   is what is reported. The reference grid used in this lab: durations
   0.1 / 1 / 10 / 100 s of network time × repeats 1 / 4 / 8 / 16 / 32.
4. **Hardware is a role, not a name.** Rows read "4-core laptop-class CPU",
   "12 GB consumer GPU", "32 GB dual-GPU workstation". The mapping to
   specific machines lives in the private deployment docs; the public
   number stands on the role because the class is what generalizes.
5. **CPU and GPU numbers are not comparable unless the precision and
   backend match.** int8 vs. fp32, CPU backend vs. GPU backend — the row
   says which.
6. **The first run of any new hardware is a calibration run** and is
   labelled as such in the report; it is not cited as the envelope.

## First measurements

The lab's first campaign (CPU baseline + the fly/shuffled/disconnected
control comparison) is running on a 4-core laptop-class host; its report
lands in [`../reports/`](../reports/README.md) with the envelope table
populated. Until then this doc is protocol-only and carries no numbers.
