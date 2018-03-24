#Our Neural Network Class
import numpy as np
import DataLoader as dl
import FileLoader as fl
import Layer as l

from time import time

def calculate_error(difference):
    error = 0
    for i in range(difference.shape[0]):
        error += np.dot(difference[i],difference[i])
    print error/difference.shape[0]

def calculate_accuracy(outputs, labels):
    correct = 0
    for i in range(outputs.shape[0]):
        if labels[i][np.argmax(outputs[i])] == 1:
            correct +=1
            #print labels[i], outputs[i]
    print float(correct)/ outputs.shape[0]

def calculate_accuracy_and_error(outputs,labels):
    difference = outputs-labels
    error = 0
    for i in range(difference.shape[0]):
        error += np.dot(difference[i],difference[i])
    error = error/difference.shape[0]
    #print 'Error:', error

    correct = 0
    for i in range(outputs.shape[0]):
        if labels[i][np.argmax(outputs[i])] == 1:
            correct +=1
    accuracy = float(correct)/ outputs.shape[0]
    #print 'Accuracy:', accuracy
    return error, accuracy


class Network:
    def __init__(self,layer_sizes=[784,300,100,10],learning_rate=1e-4,from_file=None,epsilons=[1,1,1]):
        self.learning_rate = learning_rate
        self.epsilons = epsilons
        self.layers = []
        self.dl = dl.DataLoader()

        if from_file!=None:
            arrays = fl.return_arrays(from_file)
            for i in range(len(arrays)/2):
                self.layers.append(l.Layer(W = arrays[2*i], b=arrays[2*i+1],l_obs_threshold=epsilons[i]))
        else:
            for i in range(len(layer_sizes)-1):
                self.layers.append(l.Layer(num_inputs=layer_sizes[i],num_outputs=layer_sizes[i+1],l_obs_threshold=epsilons[i]))

        self.train_images, self.train_labels = self.dl.get_training()

    def test(self):
        test_images,test_labels = self.dl.get_testing()
        outputs = self.forward(test_images)
        return calculate_accuracy_and_error(outputs,test_labels)


    def train(self,iterations=10,save_filename=None):
        t = time()
        for i in range(iterations):
            outputs = self.forward(self.train_images)

            delta_outputs = outputs-self.train_labels

            if i %1 ==0:
                print i
                calculate_error(delta_outputs)
                calculate_accuracy(outputs,self.train_labels)


            self.backward(delta_outputs)

        print 'time', time()- t

        if save_filename is not None:
            fl.store_arrays(save_filename,self.layers)



    def forward(self,inputs):
        neuron_layer = inputs
        for i in range(len(self.layers)):
            neuron_layer = self.layers[i].forward(neuron_layer)
        return neuron_layer

    def backward(self,delta_outputs):
        delta = delta_outputs
        for i in range(1,len(self.layers)):
            delta = self.layers[-i].backward(delta,self.learning_rate,new_delta_scalar=220000)

    def l_obs_prune(self, save_filename=None,max_time=10,recalculate_hessian=200,measure=500):
        self.forward(self.train_images)
        self.test()
        last_pruned_layer=0


        #Initially calculate inverse_hessian
        for layer in self.layers:
            layer.calculate_sub_inverse_hessian()

        losses = [layer.calculate_loss() for layer in self.layers]

        t = time()
        iterations = 0

        weights = self.calculate_weights()

        errors_and_accuracies = -np.ones((weights/measure,2))
        #while True and time()-t< max_time:
        while True:
            #Calculate losses
            losses[last_pruned_layer] = self.layers[last_pruned_layer].calculate_loss()

            #Find smallest loss
            min_loss = min(losses)
            if min_loss == float("inf"):
                print 'no more prunable weights', iterations, time()-t

                return

            last_pruned_layer = losses.index(min_loss)
            self.layers[last_pruned_layer].prune()

            if iterations % measure ==0:
                results = self.test()
                errors_and_accuracies[iterations/measure,:] = results
                print results, iterations

            iterations += 1

            #When the algorithm has run for long enough, recalculate the hessians
            if iterations % recalculate_hessian == 0:
                self.forward(self.train_images)
                for i in range(1, len(self.layers)):
                    self.layers[i].calculate_sub_inverse_hessian()

                for i in range(len(self.layers)):
                    losses[i] = self.layers[i].calculate_loss()


        print time() - t


        if save_filename is not None:
            fl.store_arrays(save_filename,self.layers)

        print errors_and_accuracies
        np.savetxt('report.txt',errors_and_accuracies)

    def l_obs_prune_1(self, save_filename=None,max_time=10,recalculate_hessian=200,measure=10000):
        self.forward(self.train_images)
        print self.test()
        iterations = 0
        weights = self.calculate_weights()

        #Initially calculate inverse_hessian
        for layer in self.layers:
            t = time()
            self.forward(self.train_images)
            layer.calculate_sub_inverse_hessian()
            loss = layer.calculate_loss()
            print layer.threshold

            errors_and_accuracies = -np.ones((weights/measure,2))
            while loss < layer.threshold:
                if iterations % measure ==0:
                    results = self.test()
                    errors_and_accuracies[iterations/measure,:] = results
                    print loss, results, iterations
                layer.prune()
                loss = layer.calculate_loss()
                iterations +=1
            print 'finished layer'



    def calculate_weights(self):
        weights=0
        for layer in self.layers:
            weights +=layer.W.shape[0]*layer.W.shape[1]
        return weights

    def retrain(self,iterations=2000,batches=125,save_filename=None):
        t = time()
        indices = range(0,self.train_images.shape[0]+1,self.train_images.shape[0]/batches)

        for i in range(iterations):
            for j in range(len(indices)-1):

                outputs = self.forward(self.train_images[j:j+1])

                delta_outputs = outputs-self.train_labels[j:j+1]

                #if i %1 ==0:
                    #print i
                    #print calculate_accuracy_and_error(outputs,self.train_labels[j:j+1])


                self.backward(delta_outputs)
            print self.test()
            if i % 20 == 0:
                self.shuffle_samples()

        print 'time', time()- t

    def shuffle_samples(self):
        permutation = np.random.permutation(self.train_images.shape[0])
        self.train_images = self.train_images[permutation]
        self.train_labels = self.train_labels[permutation]






if __name__ =='__main__':
    n = Network(from_file = 'save.txt',learning_rate=1e-6,epsilons=[3.16e+2,3.16e+2,2.2e+2])
    #n.train(save_filename='save.txt')
    n.retrain()
    #n.train()
    n.test()
