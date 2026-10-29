// Copyright IBM 2026

use bicycle_compiler::{PathArchitecture, language::AnglePrecision};
use pyo3::{
    exceptions::{PyTypeError, PyValueError},
    intern,
    prelude::*,
    sync::PyOnceLock,
    types::{PyDict, PyString, PyType},
};

use crate::bicycle::{CodeType, iter_pbc_circuit, measurement_table};
use qiskit_pyo3_ffi::{self as ffi, qk_circuit_num_qubits};

static QUANTUM_CIRCUIT: PyOnceLock<Py<PyType>> = PyOnceLock::new();

fn qc_type(py: Python<'_>) -> &Py<PyType> {
    QUANTUM_CIRCUIT.get_or_init(py, || {
        py.import("qiskit")
            .expect("qiskit module import failed")
            .getattr("QuantumCircuit")
            .expect("qiskit.QuantumCircuit import failed")
            .cast::<PyType>()
            .expect("failed casting to QuantumCircuit type")
            .clone()
            .unbind()
    })
}

/// Take a Qiskit QuantumCircuit instance and run the
/// bicycle_architecture_compiler on it.
/// Args:
///     circuit: The ``QuantumCircuit`` instance.
///     code: The code, either ``"gross"`` or ``"two_gross"``.
///     accuracy: The physical accuracy, either ``"1e-3"`` or ``"1e-4"``.
///
#[pyfunction]
fn estimate<'py>(
    circuit: Bound<'py, PyAny>,
    code: Bound<'py, PyString>,
    physical_error: Bound<'py, PyString>,
    epsilon: Bound<'py, PyString>,
) -> PyResult<Bound<'py, PyDict>> {
    let py = circuit.py();

    if !circuit.is_instance(qc_type(py).bind(py))? {
        return Err(PyTypeError::new_err("Input is not of type QuantumCircuit"));
    }

    let code = match code.to_str()? {
        "gross" => CodeType::Gross,
        "two_gross" => CodeType::TwoGross,
        _ => return Err(PyValueError::new_err("Invalid code")),
    };

    let model = match (&code, physical_error.to_str()?) {
        (CodeType::Gross, "1e-3") => bicycle_numerics::model::GROSS_1E3,
        (CodeType::Gross, "1e-4") => bicycle_numerics::model::GROSS_1E4,
        (CodeType::TwoGross, "1e-3") => bicycle_numerics::model::TWO_GROSS_1E3,
        (CodeType::TwoGross, "1e-4") => bicycle_numerics::model::TWO_GROSS_1E4,
        _ => return Err(PyValueError::new_err("Invalid physical error")),
    };

    let circuit_data = circuit.getattr(intern!(py, "_data"))?;
    let circuit_ptr = unsafe { ffi::qk_circuit_borrow_from_python(circuit_data.as_ptr()) };

    let num_qubits = unsafe { qk_circuit_num_qubits(circuit_ptr) };
    let arch = PathArchitecture::for_qubits(num_qubits as usize);
    let accuracy = AnglePrecision::lit(epsilon.to_str()?);
    let table = measurement_table(code);

    let bicycle = iter_pbc_circuit(circuit_ptr)
        .map_err(|e| PyTypeError::new_err(e.to_owned()))?
        .map(|op| op.compile(&arch, &table, accuracy));
    let errors = bicycle_numerics::run_numerics(bicycle, arch, model);

    let results = PyDict::new(py);

    match errors.last() {
        Some(last) => {
            results.set_item("total_error", last.total_error)?;
            results.set_item("end_time", last.end_time)?;

            let counts = PyDict::new(py);
            counts.set_item("t_injs", last.t_injs)?;
            counts.set_item("automorphisms", last.automorphisms)?;
            counts.set_item("measurements", last.measurements)?;
            counts.set_item("joint_measurements", last.joint_measurements)?;
            counts.set_item("idles", last.idles)?;

            results.set_item("counts", counts)?;
        }
        None => {
            results.set_item("total_error", 0.0)?;
            results.set_item("end_time", 0u64)?;
            results.set_item("counts", PyDict::new(py))?;
        }
    }
    Ok(results)
}

#[pymodule]
mod bicycle_architecture {
    use pyo3::prelude::*;
    use qiskit_pyo3_ffi as ffi;

    #[pymodule_init]
    fn init(m: &Bound<'_, PyModule>) -> PyResult<()> {
        ffi::qk_import(m.py())?;
        Ok(())
    }

    #[pymodule_export]
    use super::estimate;
}
