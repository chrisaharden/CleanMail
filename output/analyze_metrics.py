import csv
from collections import Counter

def read_csv(file_path):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)

def calculate_accuracy(predictions, ground_truth):
    total = len(ground_truth)
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p['Status'] == g['Status'])
    return correct / total

def calculate_metrics(predictions, ground_truth):
    true_positives = sum(1 for p, g in zip(predictions, ground_truth) if p['Status'] == 'SPAM' and g['Status'] == 'SPAM')
    false_positives = sum(1 for p, g in zip(predictions, ground_truth) if p['Status'] == 'SPAM' and g['Status'] == 'FINE')
    false_negatives = sum(1 for p, g in zip(predictions, ground_truth) if p['Status'] == 'FINE' and g['Status'] == 'SPAM')
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return precision, recall, f1_score

def main():
    ground_truth = read_csv('metrics-groundtruth.csv')
    haiku_predictions = read_csv('metrics-config-3.0-Haiku.csv')
    opus_predictions = read_csv('metrics-config-3.0-Opus.csv')
    sonnet_predictions = read_csv('metrics-config-3.5-Sonnet.csv')

    models = {
        'Haiku': haiku_predictions,
        'Opus': opus_predictions,
        'Sonnet': sonnet_predictions
    }

    print("Accuracy Analysis:")
    print("------------------")
    
    for model_name, predictions in models.items():
        accuracy = calculate_accuracy(predictions, ground_truth)
        precision, recall, f1_score = calculate_metrics(predictions, ground_truth)
        
        print(f"\n{model_name} Model:")
        print(f"Accuracy: {accuracy:.2%}")
        print(f"Precision: {precision:.2%}")
        print(f"Recall: {recall:.2%}")
        print(f"F1 Score: {f1_score:.2%}")

        # Confusion matrix
        confusion = Counter((p['Status'], g['Status']) for p, g in zip(predictions, ground_truth))
        print("\nConfusion Matrix:")
        print(f"True Positives (SPAM correctly identified): {confusion[('SPAM', 'SPAM')]}")
        print(f"False Positives (FINE incorrectly marked as SPAM): {confusion[('SPAM', 'FINE')]}")
        print(f"True Negatives (FINE correctly identified): {confusion[('FINE', 'FINE')]}")
        print(f"False Negatives (SPAM incorrectly marked as FINE): {confusion[('FINE', 'SPAM')]}")

    print("\nConclusion:")
    best_model = max(models, key=lambda m: calculate_accuracy(models[m], ground_truth))
    print(f"The {best_model} model appears to be the most accurate in predicting spam emails.")

if __name__ == "__main__":
    main()
