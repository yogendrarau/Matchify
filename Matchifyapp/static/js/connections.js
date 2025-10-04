function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(name + '=')) {
            return cookie.substring(name.length + 1);
        }
    }
    return null;
}

document.addEventListener("DOMContentLoaded", function () {
    const width = window.innerWidth;
    const height = window.innerHeight;
    let hasMoved = false;
    let container, simulation;

    let currentUserId = 1000;
    let currentUserName = null;

    const zoom = d3.zoom()
        .scaleExtent([0.5, 3])
        .translateExtent([[-width * 2, -height * 2], [width * 3, height * 3]])
        .on("zoom", zoomed);

    const svg = d3.select("#connections")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .call(zoom);

    container = svg.append("g");

    // Add filter definitions for glow effects
    const defs = svg.append("defs");

    // Glow filter for user nodes (#22c55e)
    defs.append("filter")
        .attr("id", "user-glow")
        .append("feDropShadow")
        .attr("dx", 0)
        .attr("dy", 0)
        .attr("stdDeviation", 5)
        .attr("flood-color", "#22c55e");

    // Glow filter for other nodes (#2d3748)
    defs.append("filter")
        .attr("id", "other-glow")
        .append("feDropShadow")
        .attr("dx", 0)
        .attr("dy", 0)
        .attr("stdDeviation", 5)
        .attr("flood-color", "#2d3748");

    // Glow filter for friend nodes (limegreen)
    defs.append("filter")
        .attr("id", "friend-glow")
        .append("feDropShadow")
        .attr("dx", 0)
        .attr("dy", 0)
        .attr("stdDeviation", 6) // Increase the glow size
        .attr("flood-color", "limegreen"); // Match the link color

    function zoomed(event) {
        container.attr("transform", event.transform);
        if (!hasMoved) {
            showResetButton();
            hasMoved = true;
        }
    }

    function showResetButton() {
        let resetButton = d3.select("#resetButton");

        if (resetButton.empty()) {
            resetButton = d3.select("body").append("button")
                .attr("id", "resetButton")
                .text("Reset View")
                .style("position", "absolute")
                .style("top", "10px")
                .style("left", "10px")
                .style("padding", "10px 20px")
                .style("background-color", "#1DB954")
                .style("color", "white")
                .style("border", "none")
                .style("border-radius", "5px")
                .style("cursor", "pointer")
                .style("z-index", "1000")
                .on("click", () => {
                    svg.transition().duration(750).call(
                        zoom.transform,
                        d3.zoomIdentity,
                        d3.zoomTransform(svg.node()).invert([width / 2, height / 2])
                    );
                    resetButton.style("display", "none");
                    hasMoved = false;
                });
        } else {
            resetButton.style("display", "block");
        }
    }

    // Fetch all active users
    fetch("/api/all_users")
        .then(response => response.json())
        .then(allUsersData => {
            const allUsers = allUsersData.users;

            // DEBUG: Log all user IDs and usernames
            console.log('All users:', allUsers);

            // If the server provides which user is the current user, use that ID
            const detectedCurrent = allUsers.find(u => u.isCurrentUser || u.is_current_user || u.isCurrent);
            if (detectedCurrent) {
                currentUserId = detectedCurrent.id;
                currentUserName = detectedCurrent.username || null;
            }

            console.log('detectedCurrent (from /api/all_users):', detectedCurrent);
            console.log('currentUserId:', currentUserId);

            // Fetch connections data
            fetch("/api/connections")
                .then(response => response.json())
                .then(connectionsData => {
                    console.log("API Response:", connectionsData);

                    // Do NOT add all registered users to the graph — only include nodes returned by
                    // the `/api/connections` endpoint. We may need to ensure the current user node
                    // exists so the view shows the user even if connections data omitted them.
                    const hasCurrentNode = connectionsData.nodes.some(n => n.id === currentUserId || n.isCurrentUser);
                    if (!hasCurrentNode) {
                        const currentFromAll = allUsers.find(u => u.id === currentUserId || u.isCurrentUser || u.is_current_user || u.isCurrent);
                        if (currentFromAll) {
                            connectionsData.nodes.push({
                                id: currentFromAll.id,
                                username: currentFromAll.username,
                                isCurrentUser: true,
                                isFriend: false,
                                hasPendingRequest: false
                            });
                        }
                    }

                    // Normalize IDs to strings to avoid number/string mismatches and handle
                    // link endpoints that may be objects (e.g., {id: ...}).
                    const currentUserIdStr = String(currentUserId);

                    connectionsData.nodes.forEach(node => {
                        node.id = String(node.id);
                        // Ensure isCurrentUser is set if it matches the detected current user by id or username
                        node.isCurrentUser = !!node.isCurrentUser || node.id === currentUserIdStr || (currentUserName && node.username === currentUserName);
                        if (node.isFriend == undefined) node.isFriend = false;
                        if (node.hasPendingRequest == undefined) node.hasPendingRequest = false;
                    });

                    // Normalize links so source/target are string ids
                    connectionsData.links = connectionsData.links.map(link => {
                        const rawSource = (typeof link.source === 'object' && link.source !== null) ? link.source.id : link.source;
                        const rawTarget = (typeof link.target === 'object' && link.target !== null) ? link.target.id : link.target;
                        return { source: String(rawSource), target: String(rawTarget) };
                    });

                    // Create a map to store nodes by their ID for quick lookup and DEBUG
                    let nodesById = new Map(connectionsData.nodes.map(node => [node.id, node]));
                    console.log('Node IDs (normalized):', Array.from(nodesById.keys()));
                    console.log('connectionsData.links (normalized):', connectionsData.links);
                    console.log('nodes before marking friends:', connectionsData.nodes.map(n => ({ id: n.id, username: n.username, isFriend: n.isFriend, isCurrentUser: n.isCurrentUser })));

                    // Mark nodes as friends when they are linked to the current user
                    connectionsData.links.forEach(link => {
                        try {
                            if (link.source === currentUserIdStr) {
                                const n = nodesById.get(link.target);
                                if (n) n.isFriend = true;
                            } else if (link.target === currentUserIdStr) {
                                const n = nodesById.get(link.source);
                                if (n) n.isFriend = true;
                            }
                        } catch (e) {
                            // ignore malformed links
                        }
                    });

                    // Filter the graph to only include the current user and their friends.
                    // Keep only nodes where isCurrentUser or isFriend === true.
                    const allowedNodeIds = new Set(connectionsData.nodes.filter(n => n.isCurrentUser || n.isFriend).map(n => n.id));

                    console.log('allowedNodeIds BEFORE fallback:', Array.from(allowedNodeIds));

                    // If there are no detected friends, we still want to include the current user so the view isn't empty.
                    if (!allowedNodeIds.has(currentUserIdStr)) {
                        const currentById = connectionsData.nodes.find(n => n.id === currentUserIdStr || n.isCurrentUser);
                        if (currentById) allowedNodeIds.add(currentById.id);
                    }

                    // Apply filtering to nodes and links (links now use normalized string ids)
                    connectionsData.nodes = connectionsData.nodes.filter(n => allowedNodeIds.has(n.id));
                    connectionsData.links = connectionsData.links.filter(l => allowedNodeIds.has(l.source) && allowedNodeIds.has(l.target));

                    // Rebuild nodesById to reflect the filtered nodes
                    nodesById = new Map(connectionsData.nodes.map(node => [node.id, node]));

                    // Fetch pending friend requests and only mark/draw those that are still present in the filtered graph
                    fetch("/api/pending_requests")
                        .then(response => response.json())
                        .then(data => {
                            console.log('Pending requests (post-filter):', data.pending_requests);
                            const pendingRequests = data.pending_requests || [];

                            // Update nodes with pending requests if node exists in the filtered graph
                            pendingRequests.forEach(request => {
                                const receiverId = String(request.receiver_id);
                                const node = nodesById.get(receiverId);
                                if (node) {
                                    node.hasPendingRequest = true;
                                }
                            });

                            // Draw pending links only for nodes in the filtered graph
                            const pendingLinks = pendingRequests
                                .filter(request => String(request.sender_id) === String(currentUserId))
                                .map(request => ({ source: String(currentUserId), target: String(request.receiver_id) }))
                                .filter(l => nodesById.has(l.source) && nodesById.has(l.target));

                            const pendingLinkSelection = container.append("g")
                                .attr("class", "pending-links")
                                .selectAll("line")
                                .data(pendingLinks)
                                .enter().append("line")
                                .attr("class", "pending-link")
                                .attr("stroke", "#FFD700")
                                .attr("stroke-width", 4)
                                .attr("stroke-dasharray", "8,4");

                            // Positions will be updated by the main simulation tick handler
                        })
                        .catch(error => console.error("Error fetching pending requests:", error));

                    // Find the node with the most connections
                    const nodeConnections = new Map();
                    connectionsData.links.forEach(link => {
                        nodeConnections.set(link.source, (nodeConnections.get(link.source) || 0) + 1);
                        nodeConnections.set(link.target, (nodeConnections.get(link.target) || 0) + 1);
                    });

                    const centralNode = connectionsData.nodes.reduce((maxNode, node) => {
                        const connections = nodeConnections.get(node.id) || 0;
                        return connections > (nodeConnections.get(maxNode.id) || 0) ? node : maxNode;
                    }, connectionsData.nodes[0]);

                    // Fix the central node at the center of the screen
                    centralNode.fx = width / 2;
                    centralNode.fy = height / 2;

                    simulation = d3.forceSimulation(connectionsData.nodes)
                        .force("link", d3.forceLink(connectionsData.links).id(d => d.id).distance(100))
                        .force("charge", d3.forceManyBody().strength(d => d.isCurrentUser ? 0 : -500))
                        .force("center", d3.forceCenter(width / 2, height / 2))
                        .force("x", d3.forceX(width / 2).strength(d => d.isCurrentUser ? 0 : 0.05))
                        .force("y", d3.forceY(height / 2).strength(d => d.isCurrentUser ? 0 : 0.05))
                        .force("collision", d3.forceCollide().radius(d => getNodeRadius(d) * 1.5).strength(0.5));

                    function getNodeRadius(d) {
                                        // Default to false for isFriend if not set. The graph is already
                                        // filtered to only include friends and the current user.
                                        if (d.isFriend == undefined){
                                            d.isFriend = false;
                                        }
                        return Math.max(25, d.username.length * 6);
                    }

                    function getDarkerColor(originalColor, isCurrentUser) {
                        return isCurrentUser ? "#1a8c47" : "#1e293b";
                    }

                    const link = container.append("g")
                        .selectAll("line")
                        .data(connectionsData.links)
                        .enter().append("line")
                        .attr("stroke", "limegreen")
                        .attr("stroke-width", 4)
                        .style("filter", "url(#other-glow)");

                    const nodeGroup = container.append("g")
                        .selectAll("g")
                        .data(connectionsData.nodes)
                        .enter().append("g")
                        .attr("id", d => `node-${d.id}`)  // Add ID for easy selection
                        .call(drag(simulation));

                    // Add outer circle for pending friend requests (pending-outline)
                    nodeGroup.append("circle")
                        .attr("class", "pending-outline")
                        .attr("r", d => d.hasPendingRequest ? getNodeRadius(d) * 1.2 : 0)
                        .attr("fill", "none")
                        .attr("stroke", d => d.hasPendingRequest ? "#FFD700" : "none")
                        .attr("stroke-width", 5)
                        .style("filter", d => d.hasPendingRequest ? "url(#friend-glow)" : "none")
                        .style("opacity", d => d.hasPendingRequest ? 0.8 : 0);

                    // Add a second circle for extra visibility (not the pending outline)
                    nodeGroup.append("circle")
                        .attr("r", d => getNodeRadius(d) * 1.3)
                        .attr("fill", "none")
                        .attr("stroke", d => d.hasPendingRequest ? "#FFD700" : "none")
                        .attr("stroke-width", 2)
                        .style("opacity", 0.4);

                    const node = nodeGroup.append("rect")
                        .attr("width", d => getNodeRadius(d) * 2)
                        .attr("height", d => getNodeRadius(d) * 2)
                        .attr("rx", d => getNodeRadius(d))
                        .attr("ry", d => getNodeRadius(d))
                        .attr("x", d => -getNodeRadius(d))
                        .attr("y", d => -getNodeRadius(d))
                        .attr("fill", d => d.isCurrentUser ? "#22c55e" : "#2d3748")
                        .style("filter", d => d.isCurrentUser ? "url(#user-glow)" : (d.isFriend ? "url(#friend-glow)" : "url(#other-glow)"))
                        .on("mouseover", function (event, d) {
                            const nodeElement = d3.select(this);
                            if (!d.isClicked) {
                                const enlargedSize = getNodeRadius(d) * 2.5;
                                d.currentSize = enlargedSize;

                                nodeElement.transition()
                                    .duration(200)
                                    .attr("width", enlargedSize)
                                    .attr("height", enlargedSize)
                                    .attr("x", -enlargedSize / 2)
                                    .attr("y", -enlargedSize / 2)
                                    .attr("fill", getDarkerColor(nodeElement.attr("fill"), d.isCurrentUser))
                                    .style("filter", d.isCurrentUser ? "url(#user-glow)" : (d.isFriend ? "url(#friend-glow)" : "url(#other-glow)"));

                                // Update pending-outline radius
                                d3.select(this.parentNode).select(".pending-outline")
                                    .transition()
                                    .duration(200)
                                    .attr("r", d.hasPendingRequest ? enlargedSize * 0.6 : 0)
                                    .style("opacity", d.hasPendingRequest ? 0.8 : 0);

                                d3.select(this.parentNode).select("text")
                                    .transition()
                                    .duration(200)
                                    .attr("font-size", "20px");
                            }
                        })
                        .on("mouseout", function (event, d) {
                            const nodeElement = d3.select(this);
                            if (!d.isClicked) {
                                const originalSize = getNodeRadius(d) * 2;
                                nodeElement.transition()
                                    .duration(200)
                                    .attr("width", originalSize)
                                    .attr("height", originalSize)
                                    .attr("x", -originalSize / 2)
                                    .attr("y", -originalSize / 2)
                                    .attr("fill", d.isCurrentUser ? "#22c55e" : "#2d3748")
                                    .style("filter", d.isCurrentUser ? "url(#user-glow)" : (d.isFriend ? "url(#friend-glow)" : "url(#other-glow)"));

                                // Update pending-outline radius
                                d3.select(this.parentNode).select(".pending-outline")
                                    .transition()
                                    .duration(200)
                                    .attr("r", d.hasPendingRequest ? originalSize * 0.6 : 0)
                                    .style("opacity", d.hasPendingRequest ? 0.8 : 0);

                                d3.select(this.parentNode).select("text")
                                    .transition()
                                    .duration(200)
                                    .attr("font-size", "16px");
                            } else {
                                // Reset the node if it was clicked and the cursor is still on it
                                d.isClicked = false;
                                const originalSize = getNodeRadius(d) * 2;
                                nodeElement.transition()
                                    .duration(200)
                                    .attr("rx", getNodeRadius(d))
                                    .attr("ry", getNodeRadius(d))
                                    .attr("width", originalSize)
                                    .attr("height", originalSize)
                                    .attr("x", -originalSize / 2)
                                    .attr("y", -originalSize / 2)
                                    .attr("fill", d.isCurrentUser ? "#22c55e" : "#2d3748")
                                    .style("filter", d.isCurrentUser ? "url(#user-glow)" : (d.isFriend ? "url(#friend-glow)" : "url(#other-glow)"));

                                // Update pending-outline radius
                                d3.select(this.parentNode).select(".pending-outline")
                                    .transition()
                                    .duration(200)
                                    .attr("r", d.hasPendingRequest ? originalSize * 0.6 : 0)
                                    .style("opacity", d.hasPendingRequest ? 0.8 : 0);

                                d3.select(this.parentNode).select("text")
                                    .transition()
                                    .duration(200)
                                    .attr("font-size", "16px");

                                d3.select(this.parentNode).select(".friend-request-text")
                                    .transition()
                                    .duration(200)
                                    .style("opacity", 0)
                                    .remove();
                            }
                        })
                        .on("click", function (event, d) {
                            const nodeElement = d3.select(this);
                            const currentSize = d.currentSize || getNodeRadius(d) * 2;
                            const squareSize = currentSize;

                            console.log(`Clicked on: ${d.username}, isFriend: ${d.isFriend}, isCurrentUser: ${d.isCurrentUser}`);

                            if (!d.isClicked) {
                                d.isClicked = true;

                                nodeElement.transition()
                                    .duration(300)
                                    .attr("rx", 10)
                                    .attr("ry", 10)
                                    .attr("width", squareSize)
                                    .attr("height", squareSize)
                                    .attr("x", -squareSize / 2)
                                    .attr("y", -squareSize / 2)
                                    .attr("fill", d.isCurrentUser ? "#22c55e" : "#1e293b");

                                d.fx = d.x;
                                d.fy = d.y;

                                if (!d.isFriend && !d.isCurrentUser) {
                                    d3.select(this.parentNode).append("text")
                                        .attr("class", "friend-request-text")
                                        .attr("x", 0)
                                        .attr("y", getNodeRadius(d) + 20)
                                        .attr("text-anchor", "middle")
                                        .attr("alignment-baseline", "middle")
                                        .attr("font-size", "16px")
                                        .attr("font-weight", "bold")
                                        .attr("fill", "white")
                                        .style("opacity", 0)
                                        .text("Click to send friend request")
                                        .transition()
                                        .duration(200)
                                        .style("opacity", 1);
                                }

                                let timeoutId = setTimeout(() => {
                                    d.isClicked = false;
                                    d.fx = null;
                                    d.fy = null;

                                    const originalSize = getNodeRadius(d) * 2;

                                    nodeElement.transition()
                                        .duration(500)
                                        .attr("rx", getNodeRadius(d))
                                        .attr("ry", getNodeRadius(d))
                                        .attr("width", originalSize)
                                        .attr("height", originalSize)
                                        .attr("x", -originalSize / 2)
                                        .attr("y", -originalSize / 2)
                                        .attr("fill", d.isCurrentUser ? "#22c55e" : "#2d3748")
                                        .style("filter", d.isCurrentUser ? "url(#user-glow)" : (d.isFriend ? "url(#friend-glow)" : "url(#other-glow)"));

                                    d3.select(this.parentNode).select(".friend-request-text")
                                        .transition()
                                        .duration(200)
                                        .style("opacity", 0)
                                        .remove();

                                    simulation.alpha(0.3).restart();
                                }, 10000);

                                nodeElement.on("mouseout", function () {
                                    clearTimeout(timeoutId);
                                    d.isClicked = false;
                                    d.fx = null;
                                    d.fy = null;

                                    const originalSize = getNodeRadius(d) * 2;

                                    nodeElement.transition()
                                        .duration(500)
                                        .attr("rx", getNodeRadius(d))
                                        .attr("ry", getNodeRadius(d))
                                        .attr("width", originalSize)
                                        .attr("height", originalSize)
                                        .attr("x", -originalSize / 2)
                                        .attr("y", -originalSize / 2)
                                        .attr("fill", d.isCurrentUser ? "#22c55e" : "#2d3748")
                                        .style("filter", d.isCurrentUser ? "url(#user-glow)" : (d.isFriend ? "url(#friend-glow)" : "url(#other-glow)"));

                                    d3.select(this.parentNode).select(".friend-request-text")
                                        .transition()
                                        .duration(200)
                                        .style("opacity", 0)
                                        .remove();

                                    simulation.alpha(0.3).restart();
                                });
                            } else {
                                if (d.isFriend || d.isCurrentUser) {
                                    console.log(`Navigating to profile: ${d.username}, isFriend: ${d.isFriend}`);

                                    nodeGroup.transition().duration(300).style("opacity", 0);
                                    link.transition().duration(300).style("opacity", 0);

                                    nodeElement.transition()
                                        .duration(1000)
                                        .attr("x", -width / 2)
                                        .attr("y", -height / 2)
                                        .attr("width", width * 2)
                                        .attr("height", height * 2)
                                        .attr("rx", 0)
                                        .attr("ry", 0)
                                        .attr("fill", d.isCurrentUser ? "#22c55e" : "#1e293b");

                                    setTimeout(() => {
                                        window.location.href = `/profile/${d.username}`;
                                    }, 100);
                                } else {
                                    console.log(`Access denied: ${d.username} is not a friend.`);
                                    if (d.hasPendingRequest) {
                                        alert("Friend request already sent!");
                                        return;
                                    }
                                    fetch(`/send-friend-request/${d.username}`, {
                                        method: "POST",
                                        headers: {
                                            "Content-Type": "application/json",
                                            "X-CSRFToken": getCSRFToken() // Ensure CSRF token is included
                                        }
                                    })
                                    .then(response => {
                                        if (!response.ok) {
                                            return response.json().then(data => {
                                                throw new Error(data.error || "Friend request already exists");
                                            });
                                        }
                                        return response.json();
                                    })
                                    .then(data => {
                                        if (data.success) {
                                            console.log(`Friend request sent to ${d.username}`);
                                            alert(`Friend request sent to ${d.username}!`);
                                            d.hasPendingRequest = true; // Update the node's state
                                            // Update pending-outline immediately
                                            d3.select(this.parentNode).select(".pending-outline")
                                                .transition()
                                                .duration(200)
                                                .attr("r", getNodeRadius(d) * 1.2)
                                                .attr("stroke", "#FFD700")
                                                .style("filter", "url(#friend-glow)")
                                                .style("opacity", 0.8);
                                        } else {
                                            console.error("Failed to send friend request:", data.error);
                                            if (data.error === "Friend request already exists") {
                                                alert("Friend request already sent!");
                                                d.hasPendingRequest = true; // Update the node's state
                                                d3.select(this.parentNode).select(".pending-outline")
                                                    .transition()
                                                    .duration(200)
                                                    .attr("r", getNodeRadius(d) * 1.2)
                                                    .attr("stroke", "#FFD700")
                                                    .style("filter", "url(#friend-glow)")
                                                    .style("opacity", 0.8);
                                            } else {
                                                alert(`Failed to send friend request: ${data.error}`);
                                            }
                                        }
                                    })
                                    .catch(error => {
                                        console.error("Error sending friend request:", error);
                                        if (error.message.includes("already exists")) {
                                            alert("Friend request already sent!");
                                            d.hasPendingRequest = true; // Update the node's state
                                            d3.select(this.parentNode).select(".pending-outline")
                                                .transition()
                                                .duration(200)
                                                .attr("r", getNodeRadius(d) * 1.2)
                                                .attr("stroke", "#FFD700")
                                                .style("filter", "url(#friend-glow)")
                                                .style("opacity", 0.8);
                                        } else {
                                            alert("An error occurred while sending the friend request.");
                                        }
                                    });
                                }
                            }
                        });

                    const labels = nodeGroup.append("text")
                        .text(d => d.username)
                        .attr("font-size", "16px")
                        .attr("font-weight", "bold")
                        .attr("fill", "white")
                        .attr("text-anchor", "middle")
                        .attr("alignment-baseline", "middle")
                        .style("pointer-events", "none");

                    // Single unified tick handler to update positions of links, nodes and pending links
                    simulation.on("tick", () => {
                        link
                            .attr("x1", d => d.source.x)
                            .attr("y1", d => d.source.y)
                            .attr("x2", d => d.target.x)
                            .attr("y2", d => d.target.y);

                        nodeGroup.attr("transform", d => `translate(${d.x},${d.y})`);

                        container.selectAll(".pending-link")
                            .attr("x1", d => {
                                const n = nodesById.get(d.source);
                                return n ? n.x : 0;
                            })
                            .attr("y1", d => {
                                const n = nodesById.get(d.source);
                                return n ? n.y : 0;
                            })
                            .attr("x2", d => {
                                const n = nodesById.get(d.target);
                                return n ? n.x : 0;
                            })
                            .attr("y2", d => {
                                const n = nodesById.get(d.target);
                                return n ? n.y : 0;
                            });
                    });

                    function drag(simulation) {
                        return d3.drag()
                            .on("start", (event, d) => {
                                if (!event.active) simulation.alphaTarget(0.3).restart();
                                if (!d.isClicked && d !== centralNode) {
                                    d.fx = d.x;
                                    d.fy = d.y;
                                }
                            })
                            .on("drag", (event, d) => {
                                if (!d.isClicked && d !== centralNode) {
                                    d.fx = event.x;
                                    d.fy = event.y;
                                    if (!hasMoved) {
                                        showResetButton();
                                        hasMoved = true;
                                    }
                                }
                            })
                            .on("end", (event, d) => {
                                if (!event.active) simulation.alphaTarget(0);
                                if (!d.isClicked && d !== centralNode) {
                                    d.fx = null;
                                    d.fy = null;
                                }
                            });
                        
                    }
                });
        });
});

function toggleSearchBar() {
    const searchBar = document.getElementById('searchBar');
    const goButton = document.getElementById('goButton');
    searchBar.classList.toggle('active');
    goButton.classList.toggle('active');

    if (searchBar.classList.contains('active')) {
        searchBar.focus();
    } else {
        searchBar.value = '';
    }
}

function searchUsers() {
    const query = document.getElementById('searchBar').value.toLowerCase();
    console.log("Searching for:", query);
}

function executeSearch() {
    const query = document.getElementById('searchBar').value.trim().toLowerCase();
    const searchError = document.getElementById('searchError');
    const searchBar = document.getElementById('searchBar');

    fetch("/api/all_users")
        .then(response => response.json())
        .then(data => {
            const usernames = data.users.map(user => user.username.toLowerCase());

            if (usernames.includes(query)) {
                console.log("User found:", query);
                searchError.style.display = "none";
                searchBar.style.border = "2px solid #4299e1";

                fetch("/api/connections")
                    .then(res => res.json())
                    .then(graphData => {
                        const graphUsernames = graphData.nodes.map(node => node.username.toLowerCase());
                        if (!graphUsernames.includes(query)) {
                            console.log("User is not in the graph, redirecting to profile...");
                            setTimeout(() => {
                                window.location.href = `/profile/${query}`;
                            }, 1000);
                        }
                    });

            } else {
                console.log("User does not exist:", query);
                searchError.style.display = "block";
                searchBar.style.border = "2px solid red";
            }
        });

    resetView();
}

function clearError() {
    const searchError = document.getElementById('searchError');
    const searchBar = document.getElementById('searchBar');

    searchError.style.display = "none";
    searchBar.style.border = "2px solid #4299e1";
}

function resetView() {
    const svg = d3.select("#connections svg");
    svg.transition().duration(750).call(
        d3.zoom().transform,
        d3.zoomIdentity,
        d3.zoomTransform(svg.node()).invert([window.innerWidth / 2, window.innerHeight / 2])
    );
}
