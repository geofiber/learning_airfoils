import numpy as np
from mpi4py import MPI
import tensorflow as tf
from machine_learning import NetworkInformation, OutputInformation, get_network_and_postprocess, random_seed, seed_random_number, print_memory_usage, Tables
from plot_info import *
from print_table import *
import time
import keras
import network_parameters
import copy
import os

def try_best_network_sizes(*, parameters, samples, base_title, epochs):
    optimizers = network_parameters.get_optimizers()

    losses = network_parameters.get_losses()

    selections = network_parameters.get_selections()


    class TrainingFunction(object):
        def __init__(self, *, parameters, samples, title):
            self.parameters = parameters
            self.samples=samples
            self.title = title


        def __call__(self, network_information, output_information):

            get_network_and_postprocess(self.parameters, self.samples,
                        network_information = network_information,
                        output_information = output_information)

    training_sizes = network_parameters.get_training_sizes()

    for optimizer in optimizers.keys():
        for selection_type in selections.keys():
            display(HTML("<h1>%s</h1>" % selection_type))

            for selection in selections[selection_type]:

                display(HTML("<h2>%s</h2>" % selection))

                number_of_widths = 5
                number_of_depths = 5

                if "MACHINE_LEARNING_NUMBER_OF_WIDTHS" in os.environ:
                    number_of_widths = int(os.environ["MACHINE_LEARNING_NUMBER_OF_WIDTHS"])
                    console_log("Reading number_of_widths from OS ENV. number_of_widths = {}".format(number_of_widths))
                if "MACHINE_LEARNING_NUMBER_OF_DEPTHS" in os.environ:
                    number_of_depths= int(os.environ["MACHINE_LEARNING_NUMBER_OF_DEPTHS"])
                    console_log("Reading number_of_depths from OS ENV. number_of_depths = {}".format(number_of_depths))


                for train_size in training_sizes:
                    for loss in losses:
                        regularizations = network_parameters.get_regularizations(train_size)
                        for regularization in regularizations:
                            regularization_name = "No regularization"
                            if regularization is not None:
                                if regularization.l2 > 0:
                                    regularization_name = "l2 (%f)" % regularization.l2
                                else:
                                    regularization_name = "l1 (%f)" % regularization.l1
                            display(HTML("<h4>%s</h4>" % regularization_name))

                            title = '%s\nRegularization:%s\nSelection Type: %s, Selection criterion: %s\nLoss function: %s, Optimizer: %s' % (base_title, regularization_name, selection_type, selection, loss, optimizer)
                            short_title = title
                            run_function = TrainingFunction(parameters=parameters,
                                samples = samples,
                                title = title)

                            tables = Tables.make_default()

                            network_information = NetworkInformation(optimizer=optimizers[optimizer], epochs=epochs,
                                                                     network=None, train_size=None,
                                                                     validation_size=None,
                                                                    loss=loss, tries=5,
                                                                    selection=selection, kernel_regularizer = regularization)



                            output_information = OutputInformation(tables=tables, title=title,
                                                                  short_title=title, enable_plotting=False)

                            showAndSave.prefix = '%s_%s_%s_%s_%s_%s' % (base_title, regularization_name, selection_type, selection, loss, optimizer)
                            selection_error, error_map = find_best_network_size_notebook(network_information = network_information,
                                output_information = output_information,
                                train_size = train_size,
                                run_function = run_function,
                                number_of_depths = number_of_depths,
                                number_of_widths = number_of_widths,
                                base_title = title,
                                only_selection = False)





def find_best_network_size_notebook(*, network_information,
    output_information,
    train_size,
    run_function,
    number_of_depths,
    number_of_widths,
    base_title,
    only_selection):


    base_width=6
    base_depth=4
    widths = base_width*2**np.arange(0, number_of_widths)
    depths = base_depth*2**np.arange(0, number_of_depths)

    all_depths = base_depth * 2**np.arange(0, number_of_depths+1)
    all_widths = base_width * 2**np.arange(0, number_of_widths+1)

    error_names = ["Prediction error",
                  "Error mean",
                  "Error variance",
                  "Wasserstein"]


    prediction_errors = np.zeros((len(depths), len(widths)))
    wasserstein_errors = np.zeros((len(depths), len(widths)))
    mean_errors = np.zeros((len(depths), len(widths)))
    variance_errors = np.zeros((len(depths), len(widths)))
    selection_errors = np.zeros((len(depths), len(widths)))
    prefix = copy.deepcopy(showAndSave.prefix)
    for (n,depth) in enumerate(depths):
        for (m,width) in enumerate(widths):
            print("Config {} x {} ([{} x {}] / [{} x {}])".format(depths[n], widths[m], n, m, len(depths), len(widths)))
            console_log("Config {} x {} ([{} x {}] / [{} x {}])".format(depths[n], widths[m], n, m, len(depths), len(widths)))
            seed_random_number(random_seed)
            depth = int(depth)
            width = int(width)
            network_model = [width for k in range(depth)]
            network_model.append(1)

            title='{}_{}_{}' .format (base_title, depth, width)

            network_information.train_size = train_size
            network_information.batch_size = train_size
            network_information.validation_size = train_size
            network_information.network = network_model
            output_information.enable_plotting = False
            showAndSave.silent = True
            print_comparison_table.silent = True

            showAndSave.prefix = 'network_size_{}_{}'.format(depth, width) + prefix
            start_all_training = time.time()
            with RedirectStdStreamsToNull():
                run_function(network_information, output_information)
            end_all_training = time.time()

            duration = end_all_training - start_all_training
            print("Training and postprocessing took: {} seconds ({} minutes) ({} hours)". format(duration, duration/60, duration/60/60))
            console_log("Training and postprocessing took: {} seconds ({} minutes) ({} hours)". format(duration, duration/60, duration/60/60))

            prediction_errors[n, m] = output_information.prediction_error[2]

            mean_errors[n,m] = copy.deepcopy(output_information.stat_error['mean'])
            variance_errors[n,m] = copy.deepcopy(output_information.stat_error['var'])
            wasserstein_errors[n,m] = copy.deepcopy(output_information.stat_error['wasserstein'])
            selection_errors[n,m] = copy.deepcopy(output_information.selection_error)


    showAndSave.prefix = prefix
    errors_map = {"Prediction error" : prediction_errors,
                  "Error mean" : mean_errors,
                  "Error variance" : variance_errors,
                  "Wasserstein" : wasserstein_errors,
                  "Selection error (%s)" % network_information.selection : selection_errors}

    all_errors_map = {}
    for k in errors_map.keys():
        all_errors_map[k] = errors_map[k]
    # doing this the safe way

    for error_name in errors_map.keys():
        if only_selection and 'Selection error' not in error_name:
            continue
        showAndSave.silent = False
        w,d = np.meshgrid(all_widths, all_depths)

        plt.pcolormesh(d, w, all_errors_map[error_name])

        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel("Depth")
        plt.ylabel("Width")
        plt.colorbar()
        plt.title("Experiment: {base_title}\n{error_name} with {train_size} samples\n".format(base_title=base_title,
            error_name=error_name, train_size=train_size))
        showAndSave.prefix='%s_network_%s' % (base_title, train_size)
        np.save('results/' + showAndSave.prefix + '_{}.npy'.format(error_name.replace(" ", "")), all_errors_map[error_name])
        print('all_errors_map[{error_name}]=\\ \n{errors}'.format(error_name=error_name, errors=str(all_errors_map[error_name])))
        showAndSave(error_name.replace(" ", ""))

        print_memory_usage()


    return selection_errors, errors_map
