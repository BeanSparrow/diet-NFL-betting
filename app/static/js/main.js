// Main JavaScript for Diet NFL Betting

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Format currency inputs
    const currencyInputs = document.querySelectorAll('.currency-input');
    currencyInputs.forEach(input => {
        input.addEventListener('blur', function() {
            const value = parseFloat(this.value);
            if (!isNaN(value)) {
                this.value = value.toFixed(2);
            }
        });
    });

    // Quick bet amount buttons
    const quickBetButtons = document.querySelectorAll('.quick-bet-btn');
    const betAmountInput = document.getElementById('bet-amount');
    
    quickBetButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (betAmountInput) {
                betAmountInput.value = this.dataset.amount;
            }
        });
    });

    // Team selection for betting
    const teamCards = document.querySelectorAll('.team-select-card');
    const teamInput = document.getElementById('team-picked');
    
    teamCards.forEach(card => {
        card.addEventListener('click', function() {
            // Remove selected class from all cards
            teamCards.forEach(c => c.classList.remove('selected'));
            
            // Add selected class to clicked card
            this.classList.add('selected');
            
            // Update hidden input
            if (teamInput) {
                teamInput.value = this.dataset.team;
            }
        });
    });

    // Bet form validation
    const betForm = document.getElementById('bet-form');
    if (betForm) {
        betForm.addEventListener('submit', function(e) {
            const amount = parseFloat(document.getElementById('bet-amount').value);
            const team = document.getElementById('team-picked').value;
            const maxBalance = parseFloat(document.getElementById('max-balance').value);
            
            if (!team) {
                e.preventDefault();
                alert('Please select a team to bet on.');
                return false;
            }
            
            if (isNaN(amount) || amount <= 0) {
                e.preventDefault();
                alert('Please enter a valid bet amount.');
                return false;
            }
            
            if (amount > maxBalance) {
                e.preventDefault();
                alert(`Insufficient balance. You have $${maxBalance.toFixed(2)} available.`);
                return false;
            }
            
            // Confirm bet
            const confirmMessage = `Confirm bet: $${amount.toFixed(2)} on ${team}?`;
            if (!confirm(confirmMessage)) {
                e.preventDefault();
                return false;
            }
        });
    }

    // Table sorting
    const sortableHeaders = document.querySelectorAll('.sortable');
    sortableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const columnIndex = Array.from(this.parentElement.children).indexOf(this);
            const isAscending = this.classList.contains('asc');
            
            rows.sort((a, b) => {
                const aValue = a.children[columnIndex].textContent.trim();
                const bValue = b.children[columnIndex].textContent.trim();
                
                // Try to parse as number
                const aNum = parseFloat(aValue.replace(/[$,%]/g, ''));
                const bNum = parseFloat(bValue.replace(/[$,%]/g, ''));
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return isAscending ? bNum - aNum : aNum - bNum;
                } else {
                    return isAscending ? 
                        bValue.localeCompare(aValue) : 
                        aValue.localeCompare(bValue);
                }
            });
            
            // Clear tbody and re-append sorted rows
            tbody.innerHTML = '';
            rows.forEach(row => tbody.appendChild(row));
            
            // Update sort indicators
            sortableHeaders.forEach(h => {
                h.classList.remove('asc', 'desc');
            });
            this.classList.add(isAscending ? 'desc' : 'asc');
        });
    });

    // Live balance update
    function updateBalance() {
        fetch('/api/user/balance')
            .then(response => response.json())
            .then(data => {
                const balanceElements = document.querySelectorAll('.user-balance');
                balanceElements.forEach(element => {
                    element.textContent = `$${data.balance.toFixed(2)}`;
                });
            })
            .catch(error => console.error('Error updating balance:', error));
    }

    // Update balance every 30 seconds if user is authenticated
    if (document.querySelector('.user-balance')) {
        setInterval(updateBalance, 30000);
    }

    // Countdown timer for game start times
    const countdownElements = document.querySelectorAll('.game-countdown');
    
    function updateCountdowns() {
        countdownElements.forEach(element => {
            const gameTime = new Date(element.dataset.gametime);
            const now = new Date();
            const diff = gameTime - now;
            
            if (diff > 0) {
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                
                if (hours > 24) {
                    const days = Math.floor(hours / 24);
                    element.textContent = `${days}d ${hours % 24}h`;
                } else if (hours > 0) {
                    element.textContent = `${hours}h ${minutes}m`;
                } else {
                    element.textContent = `${minutes}m`;
                }
            } else {
                element.textContent = 'Started';
                element.classList.add('text-muted');
            }
        });
    }
    
    if (countdownElements.length > 0) {
        updateCountdowns();
        setInterval(updateCountdowns, 60000); // Update every minute
    }
});

// Utility function to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Utility function to format percentage
function formatPercentage(value) {
    return `${value.toFixed(1)}%`;
}