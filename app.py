import streamlit as st
import os
import json
import random
import traceback 
from streamlit_agraph import agraph, Node, Edge, Config

def filename_from_trigger(trigger_display_name: str) -> str:
    """Converts a user-friendly trigger name to a JSON filename base."""
    return trigger_display_name.lower().replace(" ", "_")

def pretty_name_from_filename(filename: str) -> str:
    """Converts a JSON filename to a user-friendly display name."""
    if filename.endswith(".json"):
        base = filename[:-5] # Remove .json
    else:
        base = filename
    return base.replace("_", " ").title()

def get_available_triggers(directory="simulation_growth") -> list:
    """Gets a sorted list of user-friendly trigger names from JSON files in a directory."""
    trigger_names = []
    if not os.path.isdir(directory):
        st.error(f"Source directory for triggers not found: {directory}. Please ensure it exists.")
        print(f"DEBUG: Trigger directory '{directory}' not found.")
        return ["Accelerated Growth"] # Fallback
    try:
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                trigger_names.append(pretty_name_from_filename(filename))
        trigger_names.sort()
    except Exception as e:
        st.error(f"An error occurred while listing trigger files. Check console for details.")
        print(f"--- DETAILED ERROR: get_available_triggers in directory '{directory}' ---")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        traceback.print_exc()
        print(f"--- END DETAILED ERROR ---")
        return ["Accelerated Growth"] # Fallback
    if not trigger_names: # If directory is empty or no json files
        st.warning(f"No JSON files found in '{directory}'. Defaulting to 'Accelerated Growth'. Ensure JSON files are present.")
        print(f"DEBUG: No JSON files found in trigger directory '{directory}'.")
        return ["Accelerated Growth"]
    return trigger_names

def load_simulation_data(trigger_filename_base: str):
    """Loads simulation data from a JSON file in the simulation_growth directory."""
    filename = f"{trigger_filename_base}.json"
    filepath = os.path.join("simulation_growth", filename)
    if not os.path.exists(filepath):
        st.error(f"Data file not found: {filepath}. Please ensure it exists.")
        print(f"DEBUG: Simulation data file '{filepath}' not found.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error loading or parsing data for '{trigger_filename_base}'. Check console for details.")
        print(f"--- DETAILED ERROR: load_simulation_data for {filepath} ---")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        traceback.print_exc()
        print(f"--- END DETAILED ERROR ---")
        return None

def find_matching_simulation_item(simulation_items_list, centrality, connectivity, clustering):
    """
    Finds the simulation item with scores closest to the given ones (minimum Euclidean distance).
    """
    if not simulation_items_list:
        return None

    best_match = None
    min_dist_sq = float('inf')
    
    for item in simulation_items_list:
        s = item.get("scores", {})
        item_centrality = s.get("centrality", -1000.0) 
        item_connectivity = s.get("connectivity", -1000.0)
        item_clustering = s.get("clustering", -1000.0)

        dist_sq = (
            (item_centrality - centrality) ** 2 +
            (item_connectivity - connectivity) ** 2 +
            (item_clustering - clustering) ** 2
        )

        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_match = item
            
    return best_match

def display_demoviz_graph(graph_data, key_suffix="", baseline_graph_data=None):
    """Displays a graph from demoviz format using streamlit-agraph, with enhanced visual cues."""
    if not graph_data or not isinstance(graph_data, dict):
        st.warning(f"Graph data is missing or invalid for graph section '{key_suffix}'. Graph cannot be shown.")
        print(f"DEBUG: Graph data missing/invalid for display_demoviz_graph, key_suffix: {key_suffix}, data: {graph_data}")
        return

    nodes_data = graph_data.get("nodes", [])
    edges_data = graph_data.get("edges", [])

    baseline_node_ids = set()
    baseline_edge_tuples = set()

    if baseline_graph_data:
        baseline_nodes_data = baseline_graph_data.get("nodes", [])
        for node in baseline_nodes_data:
            if isinstance(node, dict) and "id" in node:
                baseline_node_ids.add(str(node["id"]))
        
        baseline_edges_data = baseline_graph_data.get("edges", [])
        for edge in baseline_edges_data:
            if isinstance(edge, dict) and "source" in edge and "target" in edge:
                s, t = str(edge["source"]), str(edge["target"])
                baseline_edge_tuples.add(tuple(sorted((s, t)))) # Store sorted for undirected comparison

    nodes_viz = []
    for node_idx, node_dict in enumerate(nodes_data):
        if not (isinstance(node_dict, dict) and "id" in node_dict):
            st.warning(f"Skipping invalid node data (index {node_idx}) for graph '{key_suffix}': {node_dict}")
            print(f"DEBUG: Invalid node data in display_demoviz_graph, key_suffix: {key_suffix}, node: {node_dict}")
            continue

        node_id_str = str(node_dict["id"])
        node_label = str(node_dict.get("label", node_id_str))
        node_role = node_dict.get("role", "default_node")
        is_new_node = baseline_graph_data and node_id_str not in baseline_node_ids

        # Default visual properties
        node_color = "#C0C0C0" # Silver for default
        node_size = 15
        node_shape = "dot" # or "ellipse", "circle", "database", "box", "text"

        # Role-based styling (takes precedence)
        if node_role == "initial_hub":
            node_color = "#FFA500" # Orange
            node_size = 20
        elif node_role == "polycentric_hub":
            node_color = "#FFD700" # Gold
            node_size = 22
        elif node_role == "central_hub":
            node_color = "#FF4500" # OrangeRed
            node_size = 25
        elif node_role == "emergent_hub":
            node_color = "#FF8C00" # DarkOrange
            node_size = 20
        elif node_role == "spoke_node":
            node_color = "#87CEEB" # SkyBlue
        elif is_new_node and node_role == "default_node": # Only if new AND default
             node_color = "#32CD32" # LimeGreen for new generic nodes
        
        # Legacy/Compatibility (if role is 'initial_node' or 'default_node' and not new, it uses default silver)

        nodes_viz.append(Node(id=node_id_str, label=node_label, size=node_size, color=node_color, shape=node_shape))
            
    edges_viz = []
    for edge_idx, edge_dict in enumerate(edges_data):
        if not (isinstance(edge_dict, dict) and "source" in edge_dict and "target" in edge_dict):
            st.warning(f"Skipping invalid edge data (index {edge_idx}) for graph '{key_suffix}': {edge_dict}")
            print(f"DEBUG: Invalid edge data in display_demoviz_graph, key_suffix: {key_suffix}, edge: {edge_dict}")
            continue

        edge_source_str = str(edge_dict["source"])
        edge_target_str = str(edge_dict["target"])
        edge_type = edge_dict.get("type", "default_link")
        
        current_edge_tuple_sorted = tuple(sorted((edge_source_str, edge_target_str)))
        is_new_edge = baseline_graph_data and current_edge_tuple_sorted not in baseline_edge_tuples

        # Default visual properties
        edge_color = "#D3D3D3" # LightGray
        edge_width = 1
        edge_dashes = False

        # Type-based styling (takes precedence)
        if edge_type == "spanning_tree_link":
            edge_color = "#A9A9A9" # DarkGray
        elif edge_type == "clustering_link" or edge_type == "local_cluster_link":
            edge_color = "#4682B4" # SteelBlue
            edge_width = 2
        elif edge_type == "hub_connection" or edge_type == "spoke_connection":
            edge_color = "#FF8C00" # DarkOrange (consistent with some hubs)
            edge_width = 2
        elif edge_type == "hub_interlink":
            edge_color = "#FF4500" # OrangeRed (stronger hub connection)
            edge_width = 2.5
        elif edge_type == "sync_enhancement_link":
            edge_color = "#20B2AA" # LightSeaGreen
        elif edge_type == "shortcut_link":
            edge_color = "#9370DB" # MediumPurple
            edge_dashes = True
            edge_width = 2
        elif edge_type == "preferential_attachment_link":
            edge_color = "#3CB371" # MediumSeaGreen
            edge_width = 1.5
        elif is_new_edge and edge_type == "default_link": # Only if new AND default
            edge_color = "#0000FF" # Blue for new generic edges
            edge_width = 2.5
        elif edge_type == "random_link":
            edge_color = "#E0E0E0" # Very light gray
        elif edge_type == "generic_added_link":
             edge_color = "#006400" # DarkGreen for specifically added generic links
             edge_width = 2
        
        # Legacy/Compatibility (if type is 'default_link' and not new, it uses default LightGray)

        edges_viz.append(Edge(source=edge_source_str, target=edge_target_str, 
                              color=edge_color, width=edge_width, dashes=edge_dashes))
            
    if not nodes_viz:
        st.warning(f"No valid nodes to display for graph '{key_suffix}'.")
        print(f"DEBUG: No valid nodes for display_demoviz_graph, key_suffix: {key_suffix}")
        return

    unique_agraph_key = f"agraph_{key_suffix}_{random.randint(1, 1000000)}" 

    config_dict = {
        "width": 500, 
        "height": 400,
        "directed": False, # Assuming graphs are generally undirected for these viz
        "physics": {"stabilization": {"iterations": 1000, "fit": True}, "barnesHut": {"gravitationalConstant": -3000}}, # Added stabilization & physics
        "hierarchical": False,
        "interaction": {"hover": True, "tooltipDelay": 200}, # Enable hover for tooltips
        "nodes": {"font": {"size": 10}}, # Smaller font size for node labels
        "edges": {"smooth": {"type": "continuous"}} # Smoother edges
    }
    config = Config(**config_dict)
    
    try:
        with st.container(key=f"container_{unique_agraph_key}"): # Ensure container also has a unique key
            agraph(nodes=nodes_viz, edges=edges_viz, config=config)
    except Exception as e:
        st.error(f"An error occurred while rendering the graph '{key_suffix}'. Check console for details.")
        print(f"--- DETAILED ERROR: display_demoviz_graph for '{key_suffix}' ---")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        traceback.print_exc()
        print(f"--- END DETAILED ERROR ---")

def community_network_assessment():
    st.title("Network Assessment Questionnaire: Organization")

    # --- Initialize session state for radio button selections if they don't exist ---
    radio_button_keys_indices = {
        "conn_freq_radio": 2, "info_flow_radio": 2, "spont_comm_radio": 2,
        "work_org_radio": 2, "group_trans_radio": 2, "know_share_radio": 2,
        "cent_conn_radio": 2, "info_brok_radio": 2, "dec_mak_radio": 2
    }
    for key, default_index in radio_button_keys_indices.items():
        if key not in st.session_state:
            st.session_state[key] = None 

    st.header("Part A – Overall Connectivity")
    connectivity_options = {
        "Very low: Only a few communicate.": 1,
        "Low: Some members communicate, but not regularly.": 2,
        "Medium: Regular communication occurs between most members.": 3,
        "High: Most members communicate frequently.": 4,
        "Very high: All members communicate consistently.": 5,
    }
    st.subheader("How often does communication occur between all members of the organization?")
    st.radio(
        "Select the frequency:", list(connectivity_options.keys()), 
        index=radio_button_keys_indices["conn_freq_radio"], 
        key="conn_freq_radio" 
    )
    
    information_flow_options = {
        "Very low: Information flow is very limited.": 1,
        "Low: Information flow occurs occasionally and is only partially accessible.": 2,
        "Medium: Information flow is consistent, but some gaps exist.": 3,
        "High: Information flow is good, and most members can access information.": 4,
        "Very high: Information flow is seamless, and everyone receives consistent access.": 5,
    }
    st.subheader("To what extent do existing processes enable continuous and accessible information flow?")
    st.radio(
        "Select the extent:", list(information_flow_options.keys()), 
        index=radio_button_keys_indices["info_flow_radio"], 
        key="info_flow_radio"
    )

    spontaneous_communication_options = {
        "Almost none occurs: organization members communicate only within formal activities.": 1,
        "Occurs minimally: Limited spontaneous communication occurs in exceptional cases.": 2,
        "Occurs moderately: Some members communicate spontaneously, but not consistently.": 3,
        "Occurs extensively: Most communicate naturally, but formal initiatives are needed sometimes.": 4,
        "Occurs naturally and consistently: Spontaneous communication is integral to daily activity.": 5,
    }
    st.subheader("To what extent does spontaneous communication occur between members?")
    st.radio(
        "Select the extent:", list(spontaneous_communication_options.keys()), 
        index=radio_button_keys_indices["spont_comm_radio"], 
        key="spont_comm_radio"
    )

    st.header("Part B – Clustering")
    workgroup_organization_options = {
        "Very low: Teamwork is almost nonexistent.": 1,
        "Low: Teamwork exists, but lacks organization.": 2,
        "Medium: Teamwork exists, but not very organized.": 3,
        "High: Teamwork is well-organized, but integration can be improved.": 4,
        "Very high: Teamwork is strong and very organized.": 5,
    }
    st.subheader("To what extent do units organize into workgroups with strong internal connections?")
    st.radio(
        "Select the extent:", list(workgroup_organization_options.keys()),
        index=radio_button_keys_indices["work_org_radio"],
        key="work_org_radio"
    )

    group_transparency_options = {
        "Very low: Minimal transparency and limited sharing.": 1,
        "Low: Transparency exists, but not consistently.": 2,
        "Medium: Good transparency, but there is room for improvement.": 3,
        "High: Most activities and updates are transparent and well-shared.": 4,
        "Very high: Full transparency and constant information sharing.": 5,
    }
    st.subheader("To what extent do mechanisms enable transparency and information sharing within groups?")
    st.radio(
        "Select the extent:", list(group_transparency_options.keys()),
        index=radio_button_keys_indices["group_trans_radio"],
        key="group_trans_radio"
    )

    knowledge_sharing_options = {
        "Very low: Knowledge sharing is actively discouraged or impossible.": 1,
        "Low: Knowledge sharing is rare and occurs only if strictly necessary.": 2,
        "Medium: Knowledge sharing occurs when prompted or facilitated.": 3,
        "High: Knowledge sharing is common and valued within workgroups.": 4,
        "Very high: Knowledge sharing is a deeply ingrained habit, happening proactively.": 5,
    }
    st.subheader("How ingrained is the habit of knowledge sharing within these workgroups?")
    st.radio(
        "Select the extent:", list(knowledge_sharing_options.keys()),
        index=radio_button_keys_indices["know_share_radio"],
        key="know_share_radio"
    )
    
    st.header("Part C – Centrality")
    central_connectors_options = {
        "Very few: Almost no individuals act as central connectors.": 1,
        "Few: Some individuals occasionally bridge different parts of the network.": 2,
        "Moderate number: Several individuals are recognized for connecting disparate groups.": 3,
        "Many: Numerous individuals actively bridge and connect different network segments.": 4,
        "Very many: Network connectivity heavily relies on a wide array of central connectors.": 5,
    }
    st.subheader("How many individuals act as central connectors, bridging different parts of the network?")
    st.radio(
        "Select the number:", list(central_connectors_options.keys()),
        index=radio_button_keys_indices["cent_conn_radio"],
        key="cent_conn_radio"
    )

    information_brokerage_options = {
        "Very ineffective: Brokers are rare, and information flow between groups is poor.": 1,
        "Ineffective: Some brokerage occurs, but it is slow and often misses key information.": 2,
        "Moderately effective: Brokers facilitate decent information flow, but with delays or gaps.": 3,
        "Effective: Brokers ensure timely and relevant information reaches different groups.": 4,
        "Very effective: Brokerage is a strong asset, ensuring rapid and comprehensive information exchange.": 5,
    }
    st.subheader("How effective are these connectors at information brokerage between groups?")
    st.radio(
        "Select the effectiveness:", list(information_brokerage_options.keys()),
        index=radio_button_keys_indices["info_brok_radio"],
        key="info_brok_radio"
    )
    
    decision_making_influence_options = {
        "Very little: Decisions are made in isolation with minimal input from connectors.": 1,
        "Little: Connectors have some input, but their influence on decisions is limited.": 2,
        "Moderate: Connectors are consulted, and their input moderately influences decisions.": 3,
        "Significant: Connectors play a key role in shaping and influencing decisions.": 4,
        "Very significant: Connectors are integral to the decision-making process; their insights are crucial.": 5,
    }
    st.subheader("How much influence do these central individuals have on decision-making processes?")
    st.radio(
        "Select the influence:", list(decision_making_influence_options.keys()),
        index=radio_button_keys_indices["dec_mak_radio"],
        key="dec_mak_radio"
    )

    if st.button("Calculate Network Scores & See Typical Visualization", key="submit_questionnaire"):
        st.session_state.questionnaire_submitted = True
        
        st.session_state.persisted_connectivity_frequency = st.session_state.conn_freq_radio
        st.session_state.persisted_information_flow = st.session_state.info_flow_radio
        st.session_state.persisted_spontaneous_communication = st.session_state.spont_comm_radio
        st.session_state.persisted_workgroup_organization = st.session_state.work_org_radio
        st.session_state.persisted_group_transparency = st.session_state.group_trans_radio
        st.session_state.persisted_knowledge_sharing = st.session_state.know_share_radio
        st.session_state.persisted_central_connectors = st.session_state.cent_conn_radio
        st.session_state.persisted_information_brokerage = st.session_state.info_brok_radio
        st.session_state.persisted_decision_making_influence = st.session_state.dec_mak_radio

        s_connectivity_frequency = connectivity_options[st.session_state.conn_freq_radio]
        s_information_flow = information_flow_options[st.session_state.info_flow_radio]
        s_spontaneous_communication = spontaneous_communication_options[st.session_state.spont_comm_radio]
        s_workgroup_organization = workgroup_organization_options[st.session_state.work_org_radio]
        s_group_transparency = group_transparency_options[st.session_state.group_trans_radio]
        s_knowledge_sharing = knowledge_sharing_options[st.session_state.know_share_radio]
        s_central_connectors = central_connectors_options[st.session_state.cent_conn_radio]
        s_information_brokerage = information_brokerage_options[st.session_state.info_brok_radio]
        s_decision_making_influence = decision_making_influence_options[st.session_state.dec_mak_radio]
        
        final_connectivity_score = (s_connectivity_frequency + s_information_flow + s_spontaneous_communication) / 3
        final_clustering_score = (s_workgroup_organization + s_group_transparency + s_knowledge_sharing) / 3
        final_centrality_score = (s_central_connectors + s_information_brokerage + s_decision_making_influence) / 3

        st.session_state.final_scores = {
            "Connectivity": final_connectivity_score,
            "Clustering": final_clustering_score,
            "Centrality": final_centrality_score,
        }
        if 'simulation_run' in st.session_state: del st.session_state.simulation_run 
        if 'current_simulation_item' in st.session_state: del st.session_state.current_simulation_item

    if st.session_state.get('questionnaire_submitted', False) and 'final_scores' in st.session_state:
        scores = st.session_state.final_scores
        st.markdown("---")
        st.header("Step 2: Calculated Network Scores")
        st.metric(label="Overall Connectivity Score", value=f"{scores['Connectivity']:.2f} / 5")
        st.metric(label="Overall Clustering Score", value=f"{scores['Clustering']:.2f} / 5")
        st.metric(label="Overall Centrality Score", value=f"{scores['Centrality']:.2f} / 5")
        
        st.markdown("**Selected Options:**")
        expander = st.expander("View your selections from the questionnaire")
        with expander:
            st.caption(f"Communication Frequency: *{st.session_state.persisted_connectivity_frequency}*")
            st.caption(f"Information Flow: *{st.session_state.persisted_information_flow}*")
            st.caption(f"Spontaneous Communication: *{st.session_state.persisted_spontaneous_communication}*")
            st.caption(f"Workgroup Organization: *{st.session_state.persisted_workgroup_organization}*")
            st.caption(f"Group Transparency: *{st.session_state.persisted_group_transparency}*")
            st.caption(f"Knowledge Sharing: *{st.session_state.persisted_knowledge_sharing}*")
            st.caption(f"Central Connectors: *{st.session_state.persisted_central_connectors}*")
            st.caption(f"Information Brokerage: *{st.session_state.persisted_information_brokerage}*")
            st.caption(f"Decision Making Influence: *{st.session_state.persisted_decision_making_influence}*")

        available_triggers = get_available_triggers()
        if not available_triggers:
            st.error("Cannot proceed without available simulation trigger contexts. Check configuration.")
            return 

        st.markdown("---")
        st.header("Step 3: Simulate & Visualize Network Strategies")

        if 'simulation_trigger' not in st.session_state or st.session_state.simulation_trigger not in available_triggers:
            st.session_state.simulation_trigger = available_triggers[0]

        selected_trigger_display = st.selectbox(
            "Select a Simulation Trigger Context:",
            options=available_triggers,
            index=available_triggers.index(st.session_state.simulation_trigger) if st.session_state.simulation_trigger in available_triggers else 0,
            key="simulation_trigger_selector" 
        )
        st.session_state.simulation_trigger = selected_trigger_display
        
        trigger_filename_base = filename_from_trigger(selected_trigger_display)
        simulation_data = load_simulation_data(trigger_filename_base)

        if simulation_data:
            matched_item = find_matching_simulation_item(
                simulation_data,
                scores["Centrality"],
                scores["Connectivity"],
                scores["Clustering"]
            )

            if matched_item:
                st.subheader(f"This is how such typical network looks like for '{selected_trigger_display}' (Scores: C={matched_item['scores']['centrality']:.1f}, N={matched_item['scores']['connectivity']:.1f}, L={matched_item['scores']['clustering']:.1f})")
                if "typical_graph_demoviz" in matched_item and matched_item["typical_graph_demoviz"]:
                    display_demoviz_graph(matched_item["typical_graph_demoviz"], key_suffix=f"typical_main_{trigger_filename_base}")
                else:
                    st.warning("Typical graph data is not available for this selection.")

                # --- Display Doubled Size Typical Graph ---
                if "doubled_size_typical_graph_demoviz" in matched_item and matched_item["doubled_size_typical_graph_demoviz"]:
                    st.subheader(f"This is how such typical network looks like at doubled size growth")
                    if "doubled_size_graph_description" in matched_item:
                        st.caption(matched_item["doubled_size_graph_description"])
                    display_demoviz_graph(matched_item["doubled_size_typical_graph_demoviz"], key_suffix=f"doubled_typical_{trigger_filename_base}")
                else:
                    st.info("Doubled size typical graph data is not available for this selection.")
                # --- End Display Doubled Size Typical Graph ---


                if st.button("Run Simulation & Show Resulting Network Topologies", key="run_simulation_button"):
                    st.session_state.simulation_run = True
                    st.session_state.current_simulation_item = matched_item 
            else:
                st.warning("No matching simulation data found for the calculated scores. Please try different questionnaire answers or check the JSON data structure.")
                if 'simulation_run' in st.session_state: del st.session_state.simulation_run
                if 'current_simulation_item' in st.session_state: del st.session_state.current_simulation_item
                    
        else:
            st.error(f"Could not load simulation data for '{selected_trigger_display}'.")
            if 'simulation_run' in st.session_state: del st.session_state.simulation_run
            if 'current_simulation_item' in st.session_state: del st.session_state.current_simulation_item

        if st.session_state.get('simulation_run', False) and 'current_simulation_item' in st.session_state:
            current_sim_item_for_display = st.session_state.current_simulation_item
            
            baseline_for_strategies = current_sim_item_for_display.get("typical_graph_demoviz")

            simulation_output_table = current_sim_item_for_display.get("simulation_output_table")
            if simulation_output_table and isinstance(simulation_output_table, list):
                for i, entry in enumerate(simulation_output_table):
                    st.markdown("---")
                    strategy_name = entry.get('Suggested Strategies', f'Strategy_{i+1}')
                    st.markdown(f"#### Strategy: {strategy_name}")
                    
                    description = entry.get("graph_change_description")
                    if description:
                        st.caption(f"Effect on Network: {description}")
                    else:
                        st.caption("Effect on Network: No specific change description available.") 

                    if "resulting_graph_demoviz" in entry and entry["resulting_graph_demoviz"]:
                        sanitized_strategy_name = "".join(c if c.isalnum() else '_' for c in strategy_name)[:30]
                        graph_key = f"resulting_{trigger_filename_base}_{i}_{sanitized_strategy_name}"
                        display_demoviz_graph(entry["resulting_graph_demoviz"], key_suffix=graph_key, baseline_graph_data=baseline_for_strategies)
                    else:
                        st.markdown("_No resulting graph available for this strategy._")
            else:
                st.info("No simulation output entries to display for the matched item.")

    if st.button("Reset Questionnaire & Selections", key="clear_questionnaire"):
        keys_to_preserve = [] 
        
        for key in list(st.session_state.keys()):
            if key not in keys_to_preserve:
                del st.session_state[key]
        
        st.session_state.questionnaire_submitted = False
        st.session_state.simulation_run = False
        st.rerun()

if __name__ == "__main__":
    if 'questionnaire_submitted' not in st.session_state:
        st.session_state.questionnaire_submitted = False
    if 'simulation_run' not in st.session_state:
        st.session_state.simulation_run = False
    
    community_network_assessment()