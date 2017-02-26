import sys
import math
import argparse
import itertools
from random import sample

from core import StatusUpdateAnalyzer, START_BATCH_SIZE
from core.data_provider import get_status_updates
from core.evaluation import calculate_metrics, write_evaluation_results
from core.utils import random_insert_seq, split_by_author
from core.utils.classifier_optimizer import ClassifierOptimizer

from crawler import crawl_status_updates


def crawl_cli(argv):
    # Create argument parser
    parser = argparse.ArgumentParser(description="This application crawls tweets from the 100 most popular twitter users and stores them on disk.")
    parser.add_argument("--output-path", "-o",
                        help="The output path of the generated dataset.")
    parser.add_argument("--user-limit", type=int, default=100,
                        help="The maximum number of accounts to crawl.")
    parser.add_argument("--limit", type=int, default=0,
                        help="The maximum number of status updates per user to crawl.")
    args = parser.parse_args(argv)

    # Extract arguments and start crawling
    crawl_status_updates('twitter', args.output_path,
                         user_limit=args.user_limit, limit=args.limit)


def analyze_cli(argv):
    # Create argument parser
    parser = argparse.ArgumentParser(description="This application evaluates the anomaly detection approach.")
    parser.add_argument("--data-source", "-t",
                        help="The data source for tweets that should be used for cross-validation. Possible values are 'fth', 'mp' and 'twitter'.")
    parser.add_argument("--dataset-path", "-p",
                        help="The path of the dataset that should be used for cross-validation.")
    parser.add_argument("--classifier-type", "-c",
                        help="The type of the classifier to be trained.")
    args = parser.parse_args(argv)

    # Get status updates
    print("Retrieving status updates...")
    status_updates = get_status_updates(args.data_source,
                                        dataset_path=args.dataset_path)

    status_updates = sorted(status_updates, key=lambda x: x.author)
    grouped_status_updates = [list(g) for k, g in itertools.groupby(status_updates, lambda x: x.author)]
    n = 500

    ClassifierOptimizer(args.classifier_type, grouped_status_updates[0][:n], grouped_status_updates[1][:n]).execute()


def evaluate_cli(argv):
    # Create argument parser
    parser = argparse.ArgumentParser(description="This application evaluates the anomaly detection approach.")
    parser.add_argument("--data-source", "-t",
                        help="The data source for tweets that should be used for cross-validation. Possible values are 'fth', 'mp' and 'twitter'.")
    parser.add_argument("--dataset-path", "-p",
                        help="The path of the dataset that should be used for cross-validation.")
    parser.add_argument("--classifier-type", "-c",
                        help="The type of the classifier to be trained.")
    parser.add_argument("--no-scaling", dest='scale_features', action='store_false',
                        help="Scale feature vector. ")
    args = parser.parse_args(argv)

    # Get status updates
    print("Retrieving status updates...")
    status_updates = get_status_updates(args.data_source,
                                        dataset_path=args.dataset_path)

    status_updates = sorted(status_updates, key=lambda x: x.author)
    grouped_status_updates = [list(g) for k, g in itertools.groupby(status_updates, lambda x: x.author)]
    n_user = 500
    evaluation_data = {}
    for i in range(len(grouped_status_updates)):
        user = grouped_status_updates[i][0].author
        print("Analyzing @%s (%s/%s)" % (user, i + 1, len(grouped_status_updates)))

        # Construct test & training sets
        user_status_updates = grouped_status_updates[i][:n_user]
        ext_status_updates = list(itertools.chain(*[x for j, x in enumerate(grouped_status_updates) if j != i]))
        ext_training_status_updates, ext_testing_status_updates = split_by_author(ext_status_updates, [user])
        if len(ext_training_status_updates) > len(user_status_updates):
            ext_training_status_updates = sample(ext_training_status_updates, len(user_status_updates))

        # Add some tweets from other users
        safe_user_status_updates = user_status_updates[:START_BATCH_SIZE]
        mixed_user_status_updates, ext_testing_status_updates = random_insert_seq(user_status_updates[START_BATCH_SIZE:],
                                                                                  ext_testing_status_updates)

        # Run classifier
        analyzer = StatusUpdateAnalyzer(safe_user_status_updates + mixed_user_status_updates,
                                        ext_training_status_updates,
                                        args.classifier_type, args.scale_features)
        analyzer.analyze()

        # Evaluation metrics
        metrics = calculate_metrics(user_status_updates[START_BATCH_SIZE:],
                                    ext_testing_status_updates,
                                    analyzer.suspicious_statuses)
        evaluation_data[user] = metrics

        tp, tn, fp, fn, prec, rec, fm, acc = metrics
        print("TP: %i, TN: %i, FP: %i, FN: %i" % (tp, tn, fp, fn))
        print("Prec: %.2f, Rec: %.2f, F: %.2f, Acc: %.2f" % (prec, rec, fm, acc))
        print()

    write_evaluation_results(evaluation_data)


if __name__ == "__main__":
    # Split arguments
    if len(sys.argv) <= 1:
        sys.exit("No action provided!")
    action = sys.argv[1]
    argv = sys.argv[2:]

    # Call sub CLI
    if action == "crawl":
        crawl_cli(argv)
    elif action == "analyze":
        analyze_cli(argv)
    elif action == "evaluate":
        evaluate_cli(argv)
    else:
        sys.exit("Invalid action!")
