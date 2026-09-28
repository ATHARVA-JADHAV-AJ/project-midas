import pandas as pd

# 1. Create a sample equipment inventory spreadsheet
data = {
    "Equipment_ID": ["COMP-101", "COMP-102", "PUMP-201", "PUMP-202", "VALVE-301"],
    "Type": ["Compressor", "Compressor", "Pump", "Pump", "Control Valve"],
    "Status": ["Active", "Maintenance", "Active", "Active", "Failed"],
    "Last_Inspection": ["2023-11-01", "2024-01-15", "2023-06-20", "2024-02-10", "2023-08-05"],
    "Next_Inspection_Due": ["2024-05-01", "2024-07-15", "2023-12-20", "2024-08-10", "2024-02-05"],
    "Q1_Spend_USD": [12000, 45000, 3000, 2500, 8000],
    "Q2_Spend_USD": [13500, 2000, 3200, 2600, 15000]
}
df = pd.DataFrame(data)
df.to_excel("test_equipment_inventory.xlsx", index=False)

# 2. Create a sample SOP text file
sop_text = """
STANDARD OPERATING PROCEDURE: EMERGENCY SHUTDOWN (UNIT 4)

1. Initial Detection: If the main reactor pressure exceeds 450 PSI, immediately sound the unit alarm.
2. Operator Assessment: The lead operator must check the primary relief valve. 
3. Decision - Valve Status: Is the primary relief valve stuck closed?
   - If YES: Proceed to manual venting (Step 4).
   - If NO: Proceed to controlled pressure bleed (Step 5).
4. Manual Venting: Open the secondary bypass valve fully. Then proceed to Step 6.
5. Controlled Bleed: Throttle the primary valve to 50% open. Then proceed to Step 6.
6. Final Shutdown: Cut feed pumps and initiate cooling water flood. Shutdown complete.
"""
with open("test_shutdown_sop.txt", "w") as f:
    f.write(sop_text.strip())

print("Test files created.")
