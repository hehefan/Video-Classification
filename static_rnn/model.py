import tensorflow as tf

class StaticRNN(object):
  def __init__(self,
               feature_size,
               num_layers,
               video_length,
               num_classes,
               cell_size,
               use_lstm,
               learning_rate=None,
               learning_rate_decay_factor=None,
               min_learning_rate=None,
               training_steps_per_epoch=None,
               max_gradient_norm=None,
               keep_prob=1.0,
               input_keep_prob=1.0,
               output_keep_prob=1.0,
               state_keep_prob=1.0,
               is_training=False):

    self.frame_feature_ph = tf.placeholder(tf.float32, [None, video_length, feature_size])
    self.video_label_ph = tf.placeholder(tf.int32, [None])

    if is_training:
      self.global_step = tf.Variable(0, trainable=False)
      self.learning_rate = tf.maximum(
          tf.train.exponential_decay(
            learning_rate,
            self.global_step,
            training_steps_per_epoch,
            learning_rate_decay_factor,
            staircase=True),
          min_learning_rate)
    # Make RNN cells
    if use_lstm:
      if num_layers > 1:
        cell = tf.contrib.rnn.MultiRNNCell(
                  cells=[tf.contrib.rnn.DropoutWrapper(
                    cell=tf.nn.rnn_cell.BasicLSTMCell(cell_size, state_is_tuple=False),
                    input_keep_prob=input_keep_prob,
                    output_keep_prob=output_keep_prob,
                    state_keep_prob=state_keep_prob) for _ in range(num_layers)],
                  state_is_tuple=False)
      else:
        cell = tf.nn.rnn_cell.BasicLSTMCell(cell_size, state_is_tuple=False)
        cell = tf.contrib.rnn.DropoutWrapper(
                  cell=cell,
                  input_keep_prob=input_keep_prob,
                  output_keep_prob=output_keep_prob,
                  state_keep_prob=state_keep_prob)
    else:
      if num_layers > 1:
        cell = tf.contrib.rnn.MultiRNNCell(
                  cells=[tf.contrib.rnn.DropoutWrapper(
                    cell=tf.nn.rnn_cell.GRUCell(cell_size),
                    input_keep_prob=input_keep_prob,
                    output_keep_prob=output_keep_prob,
                    state_keep_prob=state_keep_prob) for _ in range(num_layers)],
                  state_is_tuple=False)
      else:
        cell = tf.nn.rnn_cell.GRUCell(cell_size)
        cell = tf.contrib.rnn.DropoutWrapper(
                  cell=cell,
                  input_keep_prob=input_keep_prob,
                  output_keep_prob=output_keep_prob,
                  state_keep_prob=state_keep_prob)

    # RNN
    frame_feature = tf.split(value=self.frame_feature_ph, num_or_size_splits=video_length, axis=1)
    frame_feature = [tf.squeeze(input=f, axis=1) for f in frame_feature]

    with tf.variable_scope('StaticRNN'):
      outputs, state = tf.nn.static_rnn(cell=cell,
                                        inputs=frame_feature,
                                        dtype=tf.float32)

    state = tf.nn.dropout(state, keep_prob=keep_prob)

    with tf.variable_scope('Classifier'):
      logits = tf.contrib.layers.fully_connected(inputs=state,
                                                 num_outputs=num_classes,
                                                 activation_fn=None) # [batch_size, num_classes]
    if is_training:
      self.loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=self.video_label_ph, logits=logits))
    else:
      self.prediction = tf.argmax(logits, 1)

    if is_training:
      params = tf.trainable_variables()
      gradients = tf.gradients(self.loss, params)
      clipped_gradients, norm = tf.clip_by_global_norm(gradients, max_gradient_norm)
      self.train_op = tf.train.AdamOptimizer(self.learning_rate).apply_gradients(
        zip(clipped_gradients, params), global_step=self.global_step)

    self.saver = tf.train.Saver(tf.global_variables(), max_to_keep=0)
