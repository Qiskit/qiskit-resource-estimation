// Copyright IBM 2026

// use bicycle_common::Pauli;

#[repr(C)]
pub struct QkCircuit {
    // placeholder here since extern types are experimental
    // -- if they weren't we could just define `type QkCircuit` in the extern "C" bit
    _dummy: [u8; 0],
}

// #[repr(C)]
// pub struct PBC {
//     len: usize,
//     z: *const bool,
//     x: *const bool,
//     qubits: *const u32,
//     pub is_rotation: bool,
//     pub angle: f64,
//     pub flip: bool,
//     pub clbit: u32,
// }

// impl PBC {
//     /// # Safety
//     ///
//     /// Behavior is undefined if `self` is not initialized to a coherent PBC instruction.
//     /// In particular, `x`, `z` and `qubits` must be readable for `len` elements of correct type.
//     pub unsafe fn pauli_basis(&self, num_qubits: usize) -> Vec<Pauli> {
//         let z = unsafe { ::std::slice::from_raw_parts(self.z, self.len) };
//         let x = unsafe { ::std::slice::from_raw_parts(self.x, self.len) };
//         let qubits = unsafe { ::std::slice::from_raw_parts(self.qubits, self.len) };

//         let mut basis = vec![Pauli::I; num_qubits];

//         for ((zi, xi), qi) in z.iter().zip(x.iter()).zip(qubits.iter()) {
//             if *qi as usize >= num_qubits {
//                 panic!(
//                     "Qubit index ({}) larger than num_qubits ({})!",
//                     qi, num_qubits
//                 );
//             }

//             let pauli = match (*zi, *xi) {
//                 (true, true) => Pauli::Y,
//                 (false, true) => Pauli::X,
//                 (true, false) => Pauli::Z,
//                 (false, false) => Pauli::I,
//             };
//             basis[*qi as usize] = pauli;
//         }

//         return basis;
//     }
// }

// #[link(name = "pbc", kind = "static")]
// unsafe extern "C" {
//     pub fn get_circuit(n: u32) -> *const QkCircuit;
//     pub fn free_circuit(circuit: *const QkCircuit);
//     pub fn num_instructions(circuit: *const QkCircuit) -> usize;
//     pub fn qk_circuit_num_qubits(circuit: *const QkCircuit) -> u32;
//     pub fn get_pbc(circuit: *const QkCircuit, index: usize) -> *const PBC;
//     pub fn free_pbc(obj: *const PBC);
// }

unsafe extern "C" {
    pub fn qk_circuit_borrow_from_python(obj: *mut pyo3::ffi::PyObject) -> *mut QkCircuit;
    pub fn qk_circuit_num_qubits(circuit: *const QkCircuit) -> u32;
    pub fn qk_circuit_num_instructions(circuit: *const QkCircuit) -> usize;
    pub fn qk_circuit_free(circuit: *mut QkCircuit);
}
