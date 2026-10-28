use bicycle_compiler::{PathArchitecture, language::AnglePrecision};
use pyo3::{
    exceptions::{PyTypeError, PyValueError},
    intern,
    prelude::*,
    types::PyString,
};

// use crate::ffi::{self, QkCircuit};
use crate::bicycle::{CodeType, iter_pbc_circuit, measurement_table};
use qiskit_pyo3_ffi::{self as ffi, qk_circuit_num_qubits};

/// Take a Qiskit QuantumCircuit instance and run the
/// bicycle_architecture_compiler on it.
/// Args:
///     py_circuit: The ``QuantumCircuit`` instance.
///     code: The code, either ``"gross"`` or ``"two_gross"``.
///     accuracy: The physical accuracy, either ``"1e-3"`` or ``"1e-4"``.
///
#[pyfunction]
fn estimate(
    py_circuit: Bound<'_, PyAny>,
    code: Bound<'_, PyString>,
    physical_error: Bound<'_, PyString>,
    epsilon: Bound<'_, PyString>,
) -> PyResult<f64> {
    // TODO Do an instance check if it's actually a circuit
    let py = py_circuit.py();

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

    let circuit_data = py_circuit.getattr(intern!(py, "_data"))?;
    let circuit_ptr = unsafe { ffi::qk_circuit_borrow_from_python(circuit_data.as_ptr()) };

    let num_qubits = unsafe { qk_circuit_num_qubits(circuit_ptr) };
    let arch = PathArchitecture::for_qubits(num_qubits as usize);
    let accuracy = AnglePrecision::lit(epsilon.to_str()?);
    let table = measurement_table(code.into());

    let bicycle = iter_pbc_circuit(circuit_ptr)
        .map_err(|e| PyTypeError::new_err(e.to_owned()))?
        .map(|op| op.compile(&arch, &table, accuracy));
    let errors = bicycle_numerics::run_numerics(bicycle, arch, model);

    match errors.last() {
        Some(err) => Ok(err.total_error),
        None => Ok(0.), // the circuit was empty!
    }
}

#[pymodule]
mod _bicycle {
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
