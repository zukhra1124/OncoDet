"""
Federated learning simulation using FedAvg.

Instead of training the full DenseNet121 (way too slow on CPU), we use
a small CNN that has the same kind of structure. This lets us demo
the federated averaging algorithm with actual convergence, just without
needing a GPU or real patient data.

The setup simulates multiple hospital clients each training on their
own local data, then a central server aggregates the updates.
"""

import copy
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from config import (
    NUM_CLIENTS, FED_ROUNDS, LOCAL_EPOCHS,
    FED_BATCH_SIZE, FED_LEARNING_RATE, NUM_CLASSES
)


class LightweightOncologyNet(nn.Module):
    """
    Small CNN used just for the federated learning demo.
    Runs fast on CPU while still showing proper convergence.
    In production you'd use the full DenseNet here.
    """

    def __init__(self, num_classes=2):
        super(LightweightOncologyNet, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, kernel_size=3, padding=1),
            nn.BatchNorm2d(8),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(8, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4))
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(16 * 4 * 4, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, num_classes)
        )
    
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


def generate_synthetic_data(num_samples=30, image_size=32):
    """
    Create fake X-ray-like data for the simulation.
    Normal images get a bright center, cancer images get random
    patchy regions — enough difference for the model to learn something.
    """
    images = torch.randn(num_samples, 3, image_size, image_size) * 0.2
    
    center = image_size // 4
    span = image_size // 3
    for i in range(num_samples):
        if i < num_samples // 2:
            # "normal" — slight brightness in the middle
            images[i, :, center:center+span, center:center+span] += 0.3
        else:
            # "cancer" — random bright patch (simulates tumour)
            h = random.randint(2, image_size // 2)
            w = random.randint(2, image_size // 2)
            patch = image_size // 4
            images[i, :, h:h+patch, w:w+patch] += 0.5
    
    labels = torch.cat([
        torch.zeros(num_samples // 2, dtype=torch.long),
        torch.ones(num_samples - num_samples // 2, dtype=torch.long)
    ])
    
    # shuffle everything
    indices = torch.randperm(num_samples)
    images = images[indices]
    labels = labels[indices]
    
    return images, labels


def create_client_data_shards(num_clients=NUM_CLIENTS, samples_per_client=30):
    """Give each client its own chunk of synthetic data."""
    client_loaders = []
    
    for i in range(num_clients):
        num_samples = samples_per_client + random.randint(-10, 10)
        images, labels = generate_synthetic_data(num_samples)
        dataset = TensorDataset(images, labels)
        loader = DataLoader(dataset, batch_size=FED_BATCH_SIZE, shuffle=True)
        client_loaders.append(loader)
    
    return client_loaders


def train_client(model, dataloader, epochs=LOCAL_EPOCHS, lr=FED_LEARNING_RATE):
    """Train a model on one client's local data for a few epochs."""
    device = next(model.parameters()).device
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    metrics = {"loss": [], "accuracy": []}
    
    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        correct = 0
        total = 0
        
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
        
        epoch_loss = total_loss / len(dataloader)
        epoch_acc = correct / total if total > 0 else 0.0
        metrics["loss"].append(round(epoch_loss, 4))
        metrics["accuracy"].append(round(epoch_acc, 4))
    
    return model, metrics


def fedavg_aggregate(global_model, client_models, client_data_sizes):
    """
    FedAvg: average the client model weights, weighted by how much
    data each client has. Clients with more data get more influence.
    """
    total_data = sum(client_data_sizes)
    global_dict = global_model.state_dict()
    
    aggregated_dict = {}
    for key in global_dict.keys():
        aggregated_dict[key] = torch.zeros_like(global_dict[key], dtype=torch.float32)
    
    for client_model, data_size in zip(client_models, client_data_sizes):
        weight = data_size / total_data
        client_dict = client_model.state_dict()
        for key in aggregated_dict:
            aggregated_dict[key] += weight * client_dict[key].float()
    
    global_model.load_state_dict(aggregated_dict)
    return global_model


def evaluate_global_model(model, test_loader):
    """Check how well the global model is doing on the test set."""
    device = next(model.parameters()).device
    model.eval()
    criterion = nn.CrossEntropyLoss()
    
    total_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    return {
        "loss": round(total_loss / max(len(test_loader), 1), 4),
        "accuracy": round(correct / max(total, 1), 4)
    }


def run_federated_simulation(num_clients=NUM_CLIENTS, num_rounds=FED_ROUNDS,
                               progress_callback=None):
    """
    Run the whole federated learning loop:
    1. Create a global model and client data shards
    2. Each round: send model to clients, train locally, aggregate back
    3. Evaluate the global model after each round
    4. Return all the logs for the frontend to display
    """
    device = torch.device("cpu")
    
    global_model = LightweightOncologyNet(num_classes=NUM_CLASSES)
    global_model = global_model.to(device)
    
    client_loaders = create_client_data_shards(num_clients)
    client_data_sizes = [len(loader.dataset) for loader in client_loaders]
    
    # separate test set for evaluating the global model
    test_images, test_labels = generate_synthetic_data(40)
    test_dataset = TensorDataset(test_images, test_labels)
    test_loader = DataLoader(test_dataset, batch_size=FED_BATCH_SIZE)
    
    training_log = {
        "num_clients": num_clients,
        "num_rounds": num_rounds,
        "local_epochs": LOCAL_EPOCHS,
        "client_data_sizes": client_data_sizes,
        "rounds": [],
        "global_metrics": [],
        "client_names": [f"Hospital {chr(65 + i)}" for i in range(num_clients)]
    }
    
    print(f"\n{'='*60}")
    print(f"  Federated Learning Simulation")
    print(f"  Clients: {num_clients} | Rounds: {num_rounds}")
    print(f"  Local Epochs: {LOCAL_EPOCHS} | Batch Size: {FED_BATCH_SIZE}")
    print(f"{'='*60}\n")
    
    for round_num in range(num_rounds):
        print(f"[Round {round_num + 1}/{num_rounds}]")
        
        round_log = {
            "round": round_num + 1,
            "client_metrics": []
        }
        
        client_models = []
        
        for client_id in range(num_clients):
            # each client gets a fresh copy of the global model
            local_model = copy.deepcopy(global_model)
            trained_model, metrics = train_client(
                local_model, 
                client_loaders[client_id]
            )
            
            client_models.append(trained_model)
            
            client_log = {
                "client_id": client_id,
                "client_name": f"Hospital {chr(65 + client_id)}",
                "data_size": client_data_sizes[client_id],
                "final_loss": metrics["loss"][-1],
                "final_accuracy": metrics["accuracy"][-1],
                "loss_history": metrics["loss"],
                "accuracy_history": metrics["accuracy"]
            }
            round_log["client_metrics"].append(client_log)
            
            print(f"  Client {client_id} ({client_log['client_name']}): "
                  f"Loss={client_log['final_loss']:.4f}, "
                  f"Acc={client_log['final_accuracy']:.4f}")
        
        # aggregate all client models into the global one
        global_model = fedavg_aggregate(global_model, client_models, client_data_sizes)
        
        # see how the aggregated model performs
        global_metrics = evaluate_global_model(global_model, test_loader)
        training_log["global_metrics"].append(global_metrics)
        
        round_log["global_loss"] = global_metrics["loss"]
        round_log["global_accuracy"] = global_metrics["accuracy"]
        training_log["rounds"].append(round_log)
        
        print(f"  → Global Model: Loss={global_metrics['loss']:.4f}, "
              f"Acc={global_metrics['accuracy']:.4f}\n")
        
        if progress_callback:
            progress_callback(round_num + 1, num_rounds)
    
    print(f"{'='*60}")
    print(f"  Simulation Complete!")
    print(f"{'='*60}\n")
    
    return training_log
