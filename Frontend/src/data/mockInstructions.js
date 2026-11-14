// ========================================
// MOCK MANUFACTURING DATA
// ========================================

// Sample operation used for our MES kiosk demo.
// Later, this data can come from a real MES API.

export const operation = {
  id: "OP-1024",
  name: "Bracket Assembly",
  assembly: "System Submodule",
  serialNumber: "SN-7845632",
  station: "A-01",
  technician: "4827",

  // Each page represents a set of work instructions.
  pages: [
    {
      id: 1,
      title: "Prepare Assembly",
      instructions: [
        "Verify all required components are present.",
        "Inspect the mounting bracket.",
        "Prepare the assembly workspace.",
      ],
      steps: [
        { id: 1, title: "Verify components", completed: true },
        { id: 2, title: "Inspect mounting bracket", completed: false },
        { id: 3, title: "Prepare workspace", completed: false },
      ],
    },
    {
      id: 2,
      title: "Install Mounting Bolts",
      instructions: [
        "Position the bracket onto the frame.",
        "Insert four M6 x 1.0 bolts.",
        "Hand-tighten all bolts.",
        "Verify the bracket is properly aligned.",
      ],
      steps: [
        { id: 4, title: "Position bracket", completed: false },
        { id: 5, title: "Insert mounting bolts", completed: false },
        { id: 6, title: "Verify alignment", completed: false },
        { id: 7, title: "Inspect assembly", completed: false },
      ],
    },
    {
      id: 3,
      title: "Torque Fasteners",
      instructions: [
        "Identify the required torque specification.",
        "Verify the fastener class and stack-up.",
        "Apply torque using the approved pattern.",
        "Record torque verification.",
      ],
      steps: [
        { id: 8, title: "Verify torque specification", completed: false },
        { id: 9, title: "Torque mounting bolts", completed: false },
        { id: 10, title: "Record torque verification", completed: false },
      ],
    },
  ],
};