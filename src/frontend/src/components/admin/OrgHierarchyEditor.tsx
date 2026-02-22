import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  createCenter,
  createDepartment,
  createField,
  createTeam,
  deleteCenter,
  deleteDepartment,
  deleteField,
  deleteTeam,
} from "../../api/admin";
import { getAllocationTree } from "../../api/allocations";

export default function OrgHierarchyEditor() {
  const qc = useQueryClient();
  const { data: tree, isLoading } = useQuery({
    queryKey: ["allocation-tree"],
    queryFn: getAllocationTree,
  });

  const [newCenterName, setNewCenterName] = useState("");
  const [showAddCenter, setShowAddCenter] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const invalidateTree = () => void qc.invalidateQueries({ queryKey: ["allocation-tree"] });

  const addCenterMut = useMutation({
    mutationFn: () => createCenter({ name: newCenterName.trim() }),
    onSuccess: () => { invalidateTree(); setNewCenterName(""); setShowAddCenter(false); },
    onError: (e: Error) => setError(e.message),
  });

  const deleteCenterMut = useMutation({
    mutationFn: deleteCenter,
    onSuccess: invalidateTree,
    onError: (e: Error) => setError(e.message),
  });

  const addFieldState = useState({ centerId: "", name: "", site: "" });
  const [newField, setNewField] = addFieldState;
  const addFieldMut = useMutation({
    mutationFn: () =>
      createField({ center_id: newField.centerId, name: newField.name.trim(), site: newField.site.trim() }),
    onSuccess: () => { invalidateTree(); setNewField({ centerId: "", name: "", site: "" }); },
    onError: (e: Error) => setError(e.message),
  });

  const deleteFieldMut = useMutation({
    mutationFn: deleteField,
    onSuccess: invalidateTree,
    onError: (e: Error) => setError(e.message),
  });

  const [newDept, setNewDept] = useState({ fieldId: "", name: "" });
  const addDeptMut = useMutation({
    mutationFn: () => createDepartment({ field_id: newDept.fieldId, name: newDept.name.trim() }),
    onSuccess: () => { invalidateTree(); setNewDept({ fieldId: "", name: "" }); },
    onError: (e: Error) => setError(e.message),
  });

  const deleteDeptMut = useMutation({
    mutationFn: deleteDepartment,
    onSuccess: invalidateTree,
    onError: (e: Error) => setError(e.message),
  });

  const [newTeam, setNewTeam] = useState({ deptId: "", name: "", ldapGroupCn: "" });
  const addTeamMut = useMutation({
    mutationFn: () =>
      createTeam({
        department_id: newTeam.deptId,
        name: newTeam.name.trim(),
        ldap_group_cn: newTeam.ldapGroupCn.trim() || null,
      }),
    onSuccess: () => { invalidateTree(); setNewTeam({ deptId: "", name: "", ldapGroupCn: "" }); },
    onError: (e: Error) => setError(e.message),
  });

  const deleteTeamMut = useMutation({
    mutationFn: deleteTeam,
    onSuccess: invalidateTree,
    onError: (e: Error) => setError(e.message),
  });

  if (isLoading) return <p>Loading…</p>;

  return (
    <section>
      <h2>Org Hierarchy Editor</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Add Center */}
      <div style={{ marginBottom: 16 }}>
        <button onClick={() => setShowAddCenter((v) => !v)}>+ Add Center</button>
        {showAddCenter && (
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <input
              value={newCenterName}
              onChange={(e) => setNewCenterName(e.target.value)}
              placeholder="Center name"
            />
            <button onClick={() => addCenterMut.mutate()} disabled={!newCenterName.trim() || addCenterMut.isPending}>
              Save
            </button>
          </div>
        )}
      </div>

      {/* Centers */}
      {tree?.centers.map((center) => (
        <div key={center.center_id} style={{ border: "1px solid #ddd", padding: 12, marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <strong>Center: {center.center_name}</strong>
            <button
              onClick={() => {
                if (window.confirm(`Delete center ${center.center_name}?`)) {
                  deleteCenterMut.mutate(center.center_id);
                }
              }}
            >
              Delete
            </button>
          </div>

          {/* Add Field */}
          <div style={{ marginTop: 8 }}>
            <button
              onClick={() => setNewField({ centerId: center.center_id, name: "", site: "" })}
            >
              + Add Field
            </button>
            {newField.centerId === center.center_id && (
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <input
                  value={newField.name}
                  onChange={(e) => setNewField((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Field name"
                />
                <input
                  value={newField.site}
                  onChange={(e) => setNewField((f) => ({ ...f, site: e.target.value }))}
                  placeholder="Site (e.g. berlin)"
                />
                <button onClick={() => addFieldMut.mutate()} disabled={addFieldMut.isPending}>
                  Save
                </button>
              </div>
            )}
          </div>

          {/* Fields */}
          {center.fields.map((field) => (
            <div key={field.field_id} style={{ marginLeft: 16, marginTop: 8, borderLeft: "2px solid #eee", paddingLeft: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Field: {field.field_name} (site: {field.site})</span>
                <button
                  onClick={() => {
                    if (window.confirm(`Delete field ${field.field_name}?`)) {
                      deleteFieldMut.mutate(field.field_id);
                    }
                  }}
                >
                  Delete
                </button>
              </div>

              {/* Add Dept */}
              <button onClick={() => setNewDept({ fieldId: field.field_id, name: "" })}>
                + Add Department
              </button>
              {newDept.fieldId === field.field_id && (
                <div style={{ marginTop: 4, display: "flex", gap: 8 }}>
                  <input
                    value={newDept.name}
                    onChange={(e) => setNewDept((d) => ({ ...d, name: e.target.value }))}
                    placeholder="Department name"
                  />
                  <button onClick={() => addDeptMut.mutate()} disabled={addDeptMut.isPending}>
                    Save
                  </button>
                </div>
              )}

              {/* Departments */}
              {field.departments.map((dept) => (
                <div key={dept.dept_id} style={{ marginLeft: 16, marginTop: 4, borderLeft: "2px solid #f5f5f5", paddingLeft: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Dept: {dept.dept_name}</span>
                    <button
                      onClick={() => {
                        if (window.confirm(`Delete dept ${dept.dept_name}?`)) {
                          deleteDeptMut.mutate(dept.dept_id);
                        }
                      }}
                    >
                      Delete
                    </button>
                  </div>

                  {/* Add Team */}
                  <button onClick={() => setNewTeam({ deptId: dept.dept_id, name: "", ldapGroupCn: "" })}>
                    + Add Team
                  </button>
                  {newTeam.deptId === dept.dept_id && (
                    <div style={{ marginTop: 4, display: "flex", gap: 8 }}>
                      <input
                        value={newTeam.name}
                        onChange={(e) => setNewTeam((t) => ({ ...t, name: e.target.value }))}
                        placeholder="Team name"
                      />
                      <input
                        value={newTeam.ldapGroupCn}
                        onChange={(e) => setNewTeam((t) => ({ ...t, ldapGroupCn: e.target.value }))}
                        placeholder="LDAP group CN (optional)"
                      />
                      <button onClick={() => addTeamMut.mutate()} disabled={addTeamMut.isPending}>
                        Save
                      </button>
                    </div>
                  )}

                  {/* Teams */}
                  {dept.teams.map((team) => (
                    <div key={team.team_id} style={{ marginLeft: 16, display: "flex", justifyContent: "space-between" }}>
                      <span>Team: {team.team_name}</span>
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete team ${team.team_name}?`)) {
                            deleteTeamMut.mutate(team.team_id);
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
